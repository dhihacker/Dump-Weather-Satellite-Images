#!/usr/bin/env python3
"""
Weather Satellite Image Dumper
Downloads images from FTP server and organizes them by date
"""

import os
import sys
from ftplib import FTP, error_perm
import logging
from datetime import datetime, timedelta
import time
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SatelliteImageDownloader:
    def __init__(self, host='ntsomz.gptl.ru', port=2121, 
                 username='electro', password='electro'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_path = '/ELECTRO_L_3/2026/'
        self.local_base = Path('images')
        self.local_base.mkdir(exist_ok=True)
        
        # Month mappings (name -> number)
        self.months = {
            'January': '01', 'February': '02', 'March': '03',
            'April': '04', 'May': '05', 'June': '06',
            'July': '07', 'August': '08', 'September': '09',
            'October': '10', 'November': '11', 'December': '12'
        }
        
        # Time slots to check (24-hour format)
        self.time_slots = [f"{h:02d}{m:02d}" for h in range(24) for m in (0, 30)]

    def connect_ftp(self):
        """Establish FTP connection with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                ftp = FTP()
                ftp.connect(self.host, self.port, timeout=30)
                ftp.login(self.username, self.password)
                ftp.set_pasv(True)  # Use passive mode
                logger.info(f"Connected to {self.host}:{self.port}")
                return ftp
            except Exception as e:
                logger.error(f"FTP connection failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
        return None

    def get_remote_files(self, ftp, path):
        """Get list of files in remote directory"""
        try:
            files = []
            ftp.retrlines(f'LIST {path}', files.append)
            return files
        except error_perm as e:
            logger.debug(f"Directory {path} not accessible: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return []

    def parse_file_info(self, file_line):
        """Parse FTP LIST output to get filename"""
        parts = file_line.split()
        if len(parts) > 8:
            # Handle different LIST formats
            # Common format: -rw-r--r-- 1 user group size month day time filename
            filename = ' '.join(parts[8:])
            return filename.strip()
        return None

    def is_target_image(self, filename):
        """Check if filename matches our target pattern"""
        if not filename or not filename.endswith('.jpg'):
            return False
        
        # Check for RGB VIS IR pattern
        if '_original_RGB_VIS_IR.jpg' not in filename:
            return False
        
        # Check if filename contains any time slot
        # Example: 260303_0115_original_RGB_VIS_IR.jpg
        # The time part is after the date: YYMMDD_HHMM
        try:
            # Extract the time part (HHMM) from filename
            parts = filename.split('_')
            if len(parts) >= 2:
                time_part = parts[1]  # Should be like "0115"
                if len(time_part) == 4 and time_part.isdigit():
                    return True
        except:
            pass
            
        return False

    def download_file(self, ftp, remote_path, local_path):
        """Download a single file with retry logic"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Create local directory if it doesn't exist
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if file already exists
                if local_path.exists():
                    logger.debug(f"File already exists: {local_path}")
                    return False
                
                # Download file
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {remote_path}', f.write)
                
                logger.info(f"✅ Downloaded: {remote_path}")
                return True
                
            except Exception as e:
                logger.error(f"Error downloading {remote_path} (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
        
        return False

    def scan_and_download(self, days_back=2):
        """Scan FTP server and download new images"""
        ftp = self.connect_ftp()
        if not ftp:
            logger.error("Failed to connect to FTP server")
            return 0
        
        downloaded_count = 0
        scanned_count = 0
        
        try:
            # Calculate date range to check
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            current_date = start_date
            while current_date <= end_date:
                month_num = current_date.strftime('%m')
                day = current_date.strftime('%d')
                
                # Get month name from number
                month_name = None
                for name, num in self.months.items():
                    if num == month_num:
                        month_name = name
                        break
                
                if not month_name:
                    logger.warning(f"Could not find month name for {month_num}")
                    current_date += timedelta(days=1)
                    continue
                
                logger.info(f"Checking: 2026/{month_name}/{day}")
                
                # Construct remote path
                remote_dir = f"{self.base_path}{month_name}/{day}/"
                
                # Change to remote directory
                try:
                    ftp.cwd(remote_dir)
                except:
                    logger.debug(f"Directory not found: {remote_dir}")
                    current_date += timedelta(days=1)
                    continue
                
                # Get files in directory
                try:
                    files = ftp.nlst()
                except:
                    files = self.get_remote_files(ftp, remote_dir)
                
                if not files:
                    logger.debug(f"No files in {remote_dir}")
                    current_date += timedelta(days=1)
                    continue
                
                # Process each file
                for filename in files:
                    if not self.is_target_image(filename):
                        continue
                    
                    scanned_count += 1
                    remote_path = f"{remote_dir}{filename}"
                    local_path = self.local_base / '2026' / month_num / day / filename
                    
                    if self.download_file(ftp, remote_path, local_path):
                        downloaded_count += 1
                
                current_date += timedelta(days=1)
            
            logger.info(f"📊 Scan complete. Found: {scanned_count} matching files, Downloaded: {downloaded_count} new files")
            return downloaded_count
            
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return downloaded_count
        finally:
            try:
                ftp.quit()
            except:
                pass

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Download weather satellite images')
    parser.add_argument('--days', type=int, default=2,
                       help='Number of days back to scan (default: 2)')
    parser.add_argument('--continuous', action='store_true',
                       help='Run in continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=30,
                       help='Minutes between scans in continuous mode (default: 30)')
    
    args = parser.parse_args()
    
    downloader = SatelliteImageDownloader()
    
    if args.continuous:
        logger.info(f"Starting continuous monitoring (interval: {args.interval} minutes)")
        while True:
            try:
                count = downloader.scan_and_download(days_back=args.days)
                if count > 0:
                    logger.info(f"Downloaded {count} new images")
                
                logger.info(f"Waiting {args.interval} minutes until next scan...")
                time.sleep(args.interval * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    else:
        downloader.scan_and_download(days_back=args.days)

if __name__ == "__main__":
    main()
