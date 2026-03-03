# Weather Satellite Image Dumper

This repository automatically fetches the latest weather satellite images from a public Russian FTP server and saves them here, organized by time.

## How It Works

- Connects to: `ftp://electro:electro@ntsomz.gptl.ru:2121/ELECTRO_L_3/2026/`
- Traverses year, month (`01`-`12`), day and time structure for fresh images (e.g., `2026/03/03/0000/260303_0115_original_RGB_VIS_IR.jpg`)
- Downloads new images only
- Commits & pushes them to this GitHub repository for archiving and easy access

## Automation

A GitHub Actions workflow (`.github/workflows/dump-images.yml`) runs this script every 30 minutes.

## Usage

1. All images are under `images/YYYY/MM/DD/`.
2. To trigger an image dump manually, run the workflow from the "Actions" tab.

---

_This project is for educational and archiving purposes._
