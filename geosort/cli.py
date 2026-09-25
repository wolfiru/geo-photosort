from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from geosort.clustering import centroid, cluster_points
from geosort.config import Config, load_config
from geosort.fileops import copy_or_move_file, sanitize_name, write_report
from geosort.geocoding import NominatimGeocoder
from geosort.metadata import ExifToolNotFoundError, find_media_files, read_metadata_batch
from geosort.settings import load_settings, resolve_exiftool_path
from geosort.tagging import write_location_tags
from geosort.wizard import offer_scan_and_confirm, run_wizard


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="geosort",
        description="Sortiert Fotos/Videos anhand ihrer GPS-Position in Ordner.",
    )
    p.add_argument("--config", type=Path, help="Pfad zu einer YAML-Konfigurationsdatei")
    p.add_argument("--source", type=Path, dest="source_dir", help="Quellordner mit Fotos/Videos")
    p.add_argument("--output", type=Path, dest="output_dir", help="Zielordner (Default: <source>/GeoSort)")
    p.add_argument("--bubble-km", type=float, dest="bubble_distance_km", help="Schwellwert Bubble in km (Default 20)")
    p.add_argument("--mode", choices=["copy", "move"], dest="mode", help="copy (Default) oder move")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", default=None, help="Nur simulieren, nichts kopieren/verschieben")
    p.add_argument("--language", dest="language", help="Sprache fuer Ortsnamen (Default de)")
    p.add_argument("--exiftool-path", dest="exiftool_path", help="Pfad zu exiftool, falls nicht im PATH")
    p.add_argument(
        "--write-location-tags",
        action="store_true",
        dest="write_location_tags",
        default=None,
        help="Ort zusaetzlich als IPTC/XMP-Tags (City/State/Country + Keywords) in die Zieldatei schreiben, durchsuchbar in Explorer/Lightroom/Fotos. Datei-Zeitstempel und Aufnahmedatum bleiben unveraendert.",
    )
    p.add_argument(
        "--tag-existing",
        action="store_true",
        dest="tag_existing",
        default=None,
        help="Nur vorhandene GeoSort-Ordner (--output bzw. <source>/GeoSort) anhand ihrer Ordnernamen taggen, ohne neu zu sortieren/kopieren.",
    )
    return p


def tag_existing_tree(output_dir: Path, no_gps_dirname: str, exiftool_path: str, batch_size: int) -> int:
    tagged = 0
    for macro_dir in sorted(output_dir.iterdir()):
        if not macro_dir.is_dir() or macro_dir.name == no_gps_dirname:
            continue
        macro_name = macro_dir.name
        if " - " in macro_name:
            country, state = macro_name.split(" - ", 1)
        else:
            country, state = macro_name, None

        for bubble_dir in sorted(macro_dir.iterdir()):
            if not bubble_dir.is_dir():
                continue
            city = bubble_dir.name
            files = [p for p in bubble_dir.iterdir() if p.is_file()]
            if not files:
                continue
            write_location_tags(files, country, state, city, exiftool_path, batch_size)
            tagged += len(files)
            print(f"  {macro_name} / {city}: {len(files)} Datei(en) getaggt")
    return tagged


def run(config) -> None:
    files = find_media_files(config.source_dir, config.extensions)
    if not files:
        print(f"Keine Foto-/Videodateien in {config.source_dir} gefunden.")
        return
    print(f"{len(files)} Datei(en) gefunden. Lese Metadaten ...")

    metadata = read_metadata_batch(files, config.exiftool_path, config.batch_size)
    with_gps = [m for m in metadata if m.has_gps]
    without_gps = [m for m in metadata if not m.has_gps]
    print(f"{len(with_gps)} mit GPS-Daten, {len(without_gps)} ohne GPS-Daten.")

    geocoder = NominatimGeocoder(
        user_agent=config.user_agent,
        language=config.language,
        cache_file=config.cache_file,
        request_interval_sec=config.request_interval_sec,
    )

    report_rows = []

    # Dateien ohne GPS
    no_gps_dir = config.output_dir / config.no_gps_dirname
    for m in without_gps:
        dest = copy_or_move_file(m.path, no_gps_dir, config.mode, config.dry_run)
        report_rows.append([str(m.path), str(dest), config.no_gps_dirname, "", "", ""])

    if with_gps:
        points = [(m.lat, m.lon) for m in with_gps]
        bubble_labels = cluster_points(points, config.bubble_distance_km)

        bubble_groups: dict = defaultdict(list)
        for m, label in zip(with_gps, bubble_labels):
            bubble_groups[label].append(m)

        print(f"{len(bubble_groups)} Bubble(s) gefunden. Ermittle Ortsnamen ...")

        # Grossraum = Land + Bundesland/Region laut Geocoding (administrative
        # Grenze statt Distanz-Schwellwert). Bubble = geometrisches Clustering
        # (bubble_distance_km) innerhalb dieser Grenzen.
        macro_groups: dict = defaultdict(list)
        for bmembers in tqdm(bubble_groups.values(), desc="Bubbles", unit="Cluster"):
            bubble_points = [(m.lat, m.lon) for m in bmembers]
            bubble_center = centroid(bubble_points)
            fields = geocoder.location_fields(*bubble_center)
            raw_bubble_name = fields["city"] or fields["state"] or f"{bubble_center[0]:.3f}_{bubble_center[1]:.3f}"

            if fields["country"] and fields["state"]:
                raw_macro_name = f"{fields['country']} - {fields['state']}"
            elif fields["country"]:
                raw_macro_name = fields["country"]
            else:
                raw_macro_name = f"{bubble_center[0]:.1f}_{bubble_center[1]:.1f}"

            macro_name = sanitize_name(raw_macro_name)
            macro_groups[macro_name].append((bmembers, fields, raw_bubble_name))

        for macro_name, bubbles in macro_groups.items():
            bubble_name_counts: dict = defaultdict(int)
            for bmembers, fields, raw_bubble_name in bubbles:
                bubble_name = sanitize_name(raw_bubble_name)
                bubble_name_counts[bubble_name] += 1
                if bubble_name_counts[bubble_name] > 1:
                    bubble_name = f"{bubble_name}_{bubble_name_counts[bubble_name]}"

                dest_dir = config.output_dir / macro_name / bubble_name
                dests = []
                for m in bmembers:
                    dest = copy_or_move_file(m.path, dest_dir, config.mode, config.dry_run)
                    dests.append(dest)
                    report_rows.append([str(m.path), str(dest), macro_name, bubble_name, m.lat, m.lon])

                if config.write_location_tags and not config.dry_run:
                    write_location_tags(
                        dests,
                        fields["country"],
                        fields["state"],
                        fields["city"],
                        config.exiftool_path,
                        config.batch_size,
                    )

    report_path = config.output_dir / "geosort_report.csv"
    write_report(report_rows, report_path)
    action = "simuliert (dry-run)" if config.dry_run else ("kopiert" if config.mode == "copy" else "verschoben")
    print(f"Fertig: {len(report_rows)} Datei(en) {action}. Bericht: {report_path}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    interactive_wizard = not argv

    if interactive_wizard:
        overrides = run_wizard()
        config = Config(**overrides)
    else:
        parser = build_arg_parser()
        args = parser.parse_args(argv)
        overrides = {k: v for k, v in vars(args).items() if k != "config"}
        try:
            config = load_config(args.config, overrides)
        except ValueError as e:
            print(f"Konfigurationsfehler: {e}", file=sys.stderr)
            return 1

    settings = load_settings()
    try:
        config.exiftool_path = resolve_exiftool_path(
            settings, cli_override=config.exiftool_path, interactive=(interactive_wizard or sys.stdin.isatty())
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    try:
        if config.tag_existing:
            if not config.output_dir.is_dir():
                print(f"Zielordner nicht gefunden: {config.output_dir}", file=sys.stderr)
                return 1
            print(f"Tagge vorhandene Dateien in {config.output_dir} ...")
            count = tag_existing_tree(config.output_dir, config.no_gps_dirname, config.exiftool_path, config.batch_size)
            print(f"Fertig: {count} Datei(en) getaggt.")
        elif interactive_wizard:
            if offer_scan_and_confirm(config, run):
                run(config)
            else:
                print("Abgebrochen, es wurde nichts veraendert.")
        else:
            run(config)
    except ExifToolNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
