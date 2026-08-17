"""Online-Fix.me Steam_Fix extraction, smart anchor directory matching, and atomic injection engine."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.core.logger import get_logger
from src.steam.detector import steam_detector
from src.steam.vdf_parser import parse_vdf_file

logger = get_logger("onlinefix.installer")


@dataclass
class InstalledGameInfo:
    """Represents an installed Steam game with path, engine, and fix status."""

    app_id: int
    name: str
    install_dir_name: str
    game_path: Path
    library_path: Path
    has_online_fix: bool = False
    fix_files_found: List[str] = field(default_factory=list)
    backup_exists: bool = False
    detected_engine: str = "Unknown"  # Unreal Engine, Unity, Native/Custom, Generic
    primary_exe: Optional[str] = None
    target_subfolder: Optional[str] = None  # e.g. "Binaries/Win64" or ""


@dataclass
class FixAnalysisResult:
    """Result of analyzing an Online-Fix archive."""

    archive_path: Path
    matched_game: Optional[InstalledGameInfo] = None
    extracted_files: List[str] = field(default_factory=list)
    has_onlinefix_dll: bool = False
    has_steam_api: bool = False
    detected_game_name: Optional[str] = None
    target_relative_dir: Optional[str] = None
    confidence: float = 0.0  # 0.0 - 1.0


class OnlineFixInstaller:
    """Core algorithm for extracting, backing up, and installing Steam_Fix files with Smart Anchor resolution."""

    DEFAULT_PASSWORDS = [
        b"online-fix.me",
        b"onlinefix.me",
        b"Online-Fix.me",
        b"online-fix",
        b"",
    ]

    MANIFEST_FILENAME = ".stdp_fix_manifest.json"
    BACKUP_DIR_NAME = ".stdp_fix_backup"

    EXCLUDED_EXE_PATTERNS = [
        r"(?i)crashreport",
        r"(?i)unitycrashhandler",
        r"(?i)unins\d*",
        r"(?i)dxsetup",
        r"(?i)vcredist",
        r"(?i)easyanticheat",
        r"(?i)epicgames",
        r"(?i)steamerrorreporter",
        r"(?i)launcher",
        r"(?i)config",
        r"(?i)redist",
    ]

    def __init__(self) -> None:
        self.backup_dir_name = self.BACKUP_DIR_NAME
        self.manifest_filename = self.MANIFEST_FILENAME

    def scan_installed_games(self) -> List[InstalledGameInfo]:
        """Scan all Steam library folders to find installed games, detect engines, and fix status."""
        installed_games: List[InstalledGameInfo] = []
        steam_path = steam_detector.find_steam_path()
        if not steam_path:
            return installed_games

        libraries = steam_detector.get_library_folders(steam_path)

        for lib in libraries:
            if not lib.mounted or not lib.path.exists():
                continue

            steamapps_dir = lib.path / "steamapps"
            if not steamapps_dir.exists():
                steamapps_dir = lib.path

            common_dir = steamapps_dir / "common"
            if not common_dir.exists():
                continue

            # Check all appmanifest_<appid>.acf files
            for acf_file in steamapps_dir.glob("appmanifest_*.acf"):
                try:
                    data = parse_vdf_file(acf_file)
                    app_state = data.get("AppState") or data.get("appstate") or {}
                    if not app_state:
                        continue

                    raw_appid = app_state.get("appid")
                    if not raw_appid:
                        continue
                    app_id = int(raw_appid)

                    name = app_state.get("name") or f"App_{app_id}"
                    install_dir = app_state.get("installdir") or name

                    game_folder = common_dir / install_dir
                    if not game_folder.exists():
                        game_folder = common_dir / name

                    if not game_folder.exists() or not any(game_folder.iterdir()):
                        continue

                    # Analyze anchors (engine, steam_api64.dll location, primary exe)
                    engine, primary_exe, target_subfolder = self.detect_game_structure(game_folder)
                    has_fix, fix_files, backup_exists = self.check_game_fix_status(game_folder)

                    installed_games.append(
                        InstalledGameInfo(
                            app_id=app_id,
                            name=name,
                            install_dir_name=install_dir,
                            game_path=game_folder,
                            library_path=lib.path,
                            has_online_fix=has_fix,
                            fix_files_found=fix_files,
                            backup_exists=backup_exists,
                            detected_engine=engine,
                            primary_exe=primary_exe,
                            target_subfolder=str(target_subfolder) if target_subfolder else "",
                        )
                    )
                except Exception as e:
                    logger.debug(f"Error parsing {acf_file}: {e}")

        installed_games.sort(key=lambda g: g.name.lower())
        return installed_games

    def detect_game_structure(self, game_dir: Path) -> Tuple[str, Optional[str], Optional[Path]]:
        """Detect game engine, primary executable, and steam_api64.dll anchor folder."""
        steam_api_path: Optional[Path] = None
        all_exes: List[Path] = []
        is_unreal = False
        is_unity = False

        try:
            for root, dirs, files in os.walk(game_dir):
                if self.backup_dir_name in root:
                    continue

                r_path = Path(root)
                rel_root = r_path.relative_to(game_dir)

                for f in files:
                    f_lower = f.lower()
                    if f_lower in ["steam_api64.dll", "steam_api.dll"]:
                        steam_api_path = rel_root

                    if f_lower.endswith(".exe"):
                        is_excluded = any(re.search(pat, f_lower) for pat in self.EXCLUDED_EXE_PATTERNS)
                        if not is_excluded:
                            all_exes.append(r_path / f)

                    if "unityplayer.dll" in f_lower:
                        is_unity = True
                    if "unrealloading" in f_lower or f_lower.endswith("-win64-shipping.exe"):
                        is_unreal = True

                # Check dirs for engine signatures
                for d in dirs:
                    d_lower = d.lower()
                    if d_lower == "binaries":
                        is_unreal = True
                    if d_lower.endswith("_data"):
                        is_unity = True

        except Exception as e:
            logger.debug(f"Error inspecting structure of {game_dir}: {e}")

        # Determine engine
        if is_unreal:
            engine = "Unreal Engine"
        elif is_unity:
            engine = "Unity"
        else:
            engine = "Custom/Native"

        # Determine primary exe
        primary_exe: Optional[str] = None
        if all_exes:
            # Sort by file size descending (main game binary is usually the largest)
            try:
                all_exes.sort(key=lambda x: x.stat().st_size if x.exists() else 0, reverse=True)
                primary_exe = all_exes[0].name
            except Exception:
                primary_exe = all_exes[0].name

        return engine, primary_exe, steam_api_path

    def check_game_fix_status(self, game_dir: Path) -> Tuple[bool, List[str], bool]:
        """Check if a game folder currently contains OnlineFix files and backups."""
        if not game_dir.exists():
            return False, [], False

        found_files: List[str] = []
        backup_exists = (game_dir / self.backup_dir_name).exists() or (game_dir / self.manifest_filename).exists()

        try:
            for root, _, files in os.walk(game_dir):
                if self.backup_dir_name in root:
                    continue

                for f in files:
                    f_lower = f.lower()
                    if f_lower in ["onlinefix.ini", "onlinefix64.dll", "onlinefix.dll", "steamoverlay64.dll", "steamoverlay.dll"]:
                        found_files.append(f)
                    elif f_lower == "steam_api64.dll" and "onlinefix.ini" in [x.lower() for x in files]:
                        found_files.append("steam_api64.dll (Fix Hooked)")
        except Exception as e:
            logger.debug(f"Error checking fix status in {game_dir}: {e}")

        return len(found_files) > 0, found_files, backup_exists

    def extract_archive(self, archive_path: Path, temp_dest: Path) -> Tuple[bool, str]:
        """Extract a zip/rar/7z archive handling standard online-fix.me passwords."""
        temp_dest.mkdir(parents=True, exist_ok=True)

        if archive_path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    extracted = False
                    for pwd in self.DEFAULT_PASSWORDS:
                        try:
                            zf.extractall(path=temp_dest, pwd=pwd if pwd else None)
                            extracted = True
                            logger.info(f"Extracted {archive_path.name} with password '{pwd.decode() if pwd else 'none'}'")
                            break
                        except (RuntimeError, zipfile.BadZipFile):
                            continue

                    if not extracted:
                        return False, "ZIP arşivi şifreli ve 'online-fix.me' şifresi ile açılamadı."
                    return True, "Başarıyla ayıklandı."
            except Exception as e:
                return False, f"ZIP dosyası açılamadı: {e}"

        # 2. WinRAR / UnRAR, 7-Zip, and tar.exe support for .rar, .7z, .zip
        try:
            import subprocess

            # A. WinRAR / UnRAR (High Priority for .rar)
            # Project / Runtime bundled 7-Zip binaries
            project_root = Path(__file__).resolve().parent.parent.parent
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            user_profile = os.environ.get("USERPROFILE", "")

            # A. 7-Zip CLI (High Priority for .7z, .zip, .rar)
            seven_zip_paths = [
                str(project_root / "bundled_installers" / "7za.exe"),
                str(project_root / "bundled_installers" / "7z.exe"),
                str(project_root / "bin" / "7za.exe"),
                str(project_root / "bin" / "7z.exe"),
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe",
                os.path.join(local_appdata, r"Programs\7-Zip\7z.exe") if local_appdata else "",
                os.path.join(user_profile, r"scoop\shims\7z.exe") if user_profile else "",
                r"C:\ProgramData\chocolatey\bin\7z.exe",
                "7z",
                "7za",
            ]
            for seven_zip_exe in seven_zip_paths:
                if seven_zip_exe and (shutil.which(seven_zip_exe) or Path(seven_zip_exe).exists()):
                    for pwd in self.DEFAULT_PASSWORDS:
                        pwd_str = pwd.decode() if pwd else ""
                        cmd = [
                            str(seven_zip_exe),
                            "x",
                            str(archive_path),
                            f"-o{str(temp_dest)}",
                            f"-p{pwd_str}",
                            "-y",
                        ]
                        try:
                            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                            if res.returncode == 0 and any(temp_dest.iterdir()):
                                logger.info(f"Successfully extracted {archive_path.name} using 7-Zip.")
                                return True, "7-Zip ile başarıyla ayıklandı."
                        except Exception as e:
                            logger.debug(f"7z attempt failed: {e}")

            # B. WinRAR / UnRAR (High Priority for .rar)
            unrar_candidates = [
                r"C:\Program Files\WinRAR\UnRAR.exe",
                r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
                r"C:\Program Files\WinRAR\WinRAR.exe",
                r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
                os.path.join(local_appdata, r"Programs\WinRAR\UnRAR.exe") if local_appdata else "",
                "unrar",
                "winrar",
            ]
            for unrar_exe in unrar_candidates:
                if unrar_exe and (shutil.which(unrar_exe) or Path(unrar_exe).exists()):
                    dest_slash = str(temp_dest) + ("\\" if not str(temp_dest).endswith("\\") else "")
                    for pwd in self.DEFAULT_PASSWORDS:
                        pwd_str = pwd.decode() if pwd else ""
                        cmd = [
                            str(unrar_exe),
                            "x",
                            f"-p{pwd_str}",
                            "-y",
                            "-o+",
                            str(archive_path),
                            dest_slash,
                        ]
                        try:
                            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                            if res.returncode == 0 and any(temp_dest.iterdir()):
                                logger.info(f"Successfully extracted {archive_path.name} using UnRAR.")
                                return True, "WinRAR/UnRAR ile başarıyla ayıklandı."
                        except Exception as e:
                            logger.debug(f"UnRAR attempt failed: {e}")

            # C. System tar.exe (Windows 10/11 native fallback for non-password .tar/.zip/.gz)
            tar_paths = [r"C:\Windows\System32\tar.exe", "tar"]
            for tar_exe in tar_paths:
                if shutil.which(tar_exe) or Path(tar_exe).exists():
                    cmd = [str(tar_exe), "-xf", str(archive_path), "-C", str(temp_dest)]
                    try:
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                        if res.returncode == 0 and any(temp_dest.iterdir()):
                            logger.info(f"Successfully extracted {archive_path.name} using tar.exe.")
                            return True, "tar ile başarıyla ayıklandı."
                    except Exception as e:
                        logger.debug(f"tar attempt failed: {e}")

        except Exception as e:
            logger.debug(f"Extended extractor error: {e}")

        return (
            False,
            f"'{archive_path.suffix}' formatındaki şifreli arşiv açılamadı.\n"
            f"Sistemde 7-Zip veya WinRAR bulunamadı.\n"
            f"Lütfen 'BAGIMLILIKLARI_KUR.bat' çalıştırın veya 7-Zip / WinRAR kurun."
        )

    def analyze_fix_archive(self, archive_path: Path, installed_games: List[InstalledGameInfo]) -> FixAnalysisResult:
        """Analyze archive contents and smartly match it to one of the installed Steam games."""
        temp_dir = Path(tempfile.mkdtemp(prefix="STDP_FixAnalyze_"))
        result = FixAnalysisResult(archive_path=archive_path)

        try:
            success, _ = self.extract_archive(archive_path, temp_dir)
            if not success:
                return result

            all_files: List[Path] = []
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    all_files.append(Path(root) / f)

            result.extracted_files = [str(f.relative_to(temp_dir)) for f in all_files]

            for f in all_files:
                name_l = f.name.lower()
                if "onlinefix" in name_l:
                    result.has_onlinefix_dll = True
                if "steam_api" in name_l:
                    result.has_steam_api = True

            raw_stem = archive_path.stem
            cleaned_stem = re.sub(r"(?i)(fix|repair|steam_fix|online-fix|onlinefix|v\d+.*|\.me|_me)", "", raw_stem)
            cleaned_stem = re.sub(r"[._\-+]+", " ", cleaned_stem).strip()
            result.detected_game_name = cleaned_stem

            best_match: Optional[InstalledGameInfo] = None
            highest_score = 0.0

            for game in installed_games:
                score = self._calculate_match_score(cleaned_stem, game.name, game.install_dir_name)
                if score > highest_score and score >= 0.5:
                    highest_score = score
                    best_match = game

            result.matched_game = best_match
            result.confidence = highest_score

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return result

    def _calculate_match_score(self, query: str, game_name: str, install_dir: str) -> float:
        """Calculate matching score between archive name and game name/folder."""
        q = query.lower()
        g = game_name.lower()
        d = install_dir.lower()

        if q == g or q == d:
            return 1.0
        if q in g or g in q or q in d or d in q:
            return 0.85

        q_words = set(re.findall(r"\w+", q))
        g_words = set(re.findall(r"\w+", g))
        if not q_words or not g_words:
            return 0.0

        overlap = len(q_words.intersection(g_words))
        return overlap / max(len(q_words), len(g_words))

    def resolve_file_mapping(
        self,
        source_root: Path,
        target_game_path: Path,
        target_subfolder: Optional[Path] = None,
    ) -> List[Tuple[Path, Path]]:
        """Calculate (source_file, target_file) mappings respecting Smart Anchor directory depth."""
        # Check if source_root has steam_api64.dll at its root or inside a subfolder
        source_steam_api_rel: Optional[Path] = None
        for root, _, files in os.walk(source_root):
            for f in files:
                if f.lower() in ["steam_api64.dll", "steam_api.dll"]:
                    source_steam_api_rel = Path(root).relative_to(source_root)
                    break
            if source_steam_api_rel:
                break

        # If source has steam_api64.dll in its root (flat) but the game has it in a subfolder (e.g. Binaries/Win64)
        use_subfolder_offset = False
        if target_subfolder and str(target_subfolder) not in [".", ""]:
            if source_steam_api_rel is None or str(source_steam_api_rel) in [".", ""]:
                use_subfolder_offset = True

        mappings: List[Tuple[Path, Path]] = []
        for root, _, files in os.walk(source_root):
            rel_dir = Path(root).relative_to(source_root)
            for f in files:
                src_file = Path(root) / f

                if use_subfolder_offset and target_subfolder:
                    # Place relative to target_subfolder
                    dst_file = target_game_path / target_subfolder / rel_dir / f
                else:
                    # Place relative to game root
                    dst_file = target_game_path / rel_dir / f

                mappings.append((src_file, dst_file))

        return mappings

    def install_fix(
        self,
        archive_path: Path,
        target_game: InstalledGameInfo,
        custom_nickname: Optional[str] = None,
        custom_language: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Atomically extract and install fix with backup and manifest recording."""
        if not target_game.game_path.exists():
            return False, f"Hedef oyun dizini bulunamadı: {target_game.game_path}"

        temp_dir = Path(tempfile.mkdtemp(prefix="STDP_FixInstall_"))
        backup_dir = target_game.game_path / self.backup_dir_name
        manifest_file = target_game.game_path / self.manifest_filename

        backed_up_rel_files: List[str] = []
        created_rel_files: List[str] = []

        try:
            # 1. Extract archive
            success, msg = self.extract_archive(archive_path, temp_dir)
            if not success:
                return False, msg

            # 2. Unwrap single top-level folder if archive wraps everything in GameName/
            source_root = temp_dir
            subdirs = [p for p in temp_dir.iterdir() if p.is_dir()]
            files_in_root = [p for p in temp_dir.iterdir() if p.is_file()]
            if len(subdirs) == 1 and not files_in_root:
                source_root = subdirs[0]

            # 3. Detect smart anchor target subfolder (e.g. Binaries/Win64)
            _, _, anchor_subfolder = self.detect_game_structure(target_game.game_path)
            file_mappings = self.resolve_file_mapping(source_root, target_game.game_path, anchor_subfolder)

            if not file_mappings:
                return False, "Arşiv içinde kurulacak geçerli bir dosya bulunamadı."

            # 4. Create Backups of files that will be overwritten
            backup_dir.mkdir(parents=True, exist_ok=True)

            for _, dst_file in file_mappings:
                rel_to_game = str(dst_file.relative_to(target_game.game_path)).replace("\\", "/")
                if dst_file.exists() and dst_file.is_file():
                    backup_target = backup_dir / rel_to_game
                    backup_target.parent.mkdir(parents=True, exist_ok=True)
                    if not backup_target.exists():
                        shutil.copy2(dst_file, backup_target)
                        backed_up_rel_files.append(rel_to_game)
                        logger.info(f"Backed up original: {rel_to_game}")
                else:
                    created_rel_files.append(rel_to_game)

            # 5. Copy Fix Files to Game Directory (Atomic copy)
            for src_file, dst_file in file_mappings:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                logger.info(f"Installed fix file -> {dst_file}")

            # 6. Configure OnlineFix.ini
            self._configure_ini_files(target_game.game_path, custom_nickname, custom_language)

            # 7. Write Manifest File
            manifest_data = {
                "game_name": target_game.name,
                "app_id": target_game.app_id,
                "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "engine": target_game.detected_engine,
                "target_subfolder": str(anchor_subfolder) if anchor_subfolder else "",
                "backed_up_files": backed_up_rel_files,
                "created_files": created_rel_files,
            }
            manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

            dest_hint = f" ({anchor_subfolder})" if anchor_subfolder and str(anchor_subfolder) != "." else ""
            return True, f"'{target_game.name}'{dest_hint} için Steam_Fix başarıyla kuruldu!\nOrijinal dosyalar güvenle yedeklendi."

        except Exception as e:
            logger.error(f"Failed to install fix to {target_game.name}: {e}")
            # Rollback in case of failure
            self.revert_fix(target_game)
            return False, f"Fix yüklenirken hata oluştu (işlem geri alındı): {e}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _configure_ini_files(
        self,
        game_path: Path,
        nickname: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        """Modify OnlineFix.ini to set nickname or language if requested."""
        for root, _, files in os.walk(game_path):
            if self.backup_dir_name in root:
                continue
            for f in files:
                if f.lower() == "onlinefix.ini":
                    ini_path = Path(root) / f
                    try:
                        content = ini_path.read_text(encoding="utf-8", errors="ignore")
                        lines = content.splitlines()
                        new_lines = []
                        for line in lines:
                            if nickname and line.strip().lower().startswith("fakename"):
                                new_lines.append(f"FakeName={nickname}")
                            elif nickname and line.strip().lower().startswith("accountname"):
                                new_lines.append(f"AccountName={nickname}")
                            elif language and line.strip().lower().startswith("language"):
                                new_lines.append(f"Language={language}")
                            else:
                                new_lines.append(line)
                        ini_path.write_text("\n".join(new_lines), encoding="utf-8")
                        logger.info(f"Updated {ini_path.name} with custom settings.")
                    except Exception as e:
                        logger.debug(f"Failed to customize {ini_path}: {e}")

    def revert_fix(self, target_game: InstalledGameInfo) -> Tuple[bool, str]:
        """Remove installed OnlineFix files and restore original backed-up game files cleanly."""
        if not target_game.game_path.exists():
            return False, "Oyun klasörü bulunamadı."

        backup_dir = target_game.game_path / self.backup_dir_name
        manifest_file = target_game.game_path / self.manifest_filename

        restored_count = 0
        deleted_count = 0

        try:
            # 1. Revert using Manifest if available
            if manifest_file.exists():
                try:
                    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    backed_up = manifest_data.get("backed_up_files", [])
                    created = manifest_data.get("created_files", [])

                    # Restore backed up
                    for rel_p in backed_up:
                        src_bak = backup_dir / rel_p
                        dst_file = target_game.game_path / rel_p
                        if src_bak.exists():
                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_bak, dst_file)
                            restored_count += 1

                    # Remove created
                    for rel_p in created:
                        target_f = target_game.game_path / rel_p
                        if target_f.exists() and target_f.is_file():
                            try:
                                target_f.unlink()
                                deleted_count += 1
                            except Exception:
                                pass

                    manifest_file.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Error parsing manifest during revert: {e}")

            # 2. Fallback folder restoration if backup_dir exists
            if backup_dir.exists():
                for root, _, files in os.walk(backup_dir):
                    rel_dir = Path(root).relative_to(backup_dir)
                    for f in files:
                        src_backup = Path(root) / f
                        dst_file = target_game.game_path / rel_dir / f
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_backup, dst_file)
                        restored_count += 1

                # Clean OnlineFix specific leftovers
                for root, _, files in os.walk(target_game.game_path):
                    if self.backup_dir_name in root:
                        continue
                    for f in files:
                        if f.lower() in ["onlinefix.ini", "onlinefix64.dll", "onlinefix.dll", "steamoverlay64.dll", "steamoverlay.dll"]:
                            try:
                                (Path(root) / f).unlink()
                                deleted_count += 1
                            except Exception:
                                pass

                shutil.rmtree(backup_dir, ignore_errors=True)

            if restored_count == 0 and deleted_count == 0 and not (target_game.game_path / self.manifest_filename).exists():
                return False, "Bu oyun için geri yüklenecek bir yedek veya fix bulunamadı."

            return True, f"'{target_game.name}' orijinal haline döndürüldü! ({restored_count} dosya geri yüklendi, {deleted_count} ek dosya temizlendi)"

        except Exception as e:
            logger.error(f"Failed to revert fix for {target_game.name}: {e}")
            return False, f"Geri yükleme sırasında hata oluştu: {e}"


# Global singleton instance
online_fix_installer = OnlineFixInstaller()
