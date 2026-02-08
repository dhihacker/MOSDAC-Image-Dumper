#!/usr/bin/env python3
"""
MOSDAC Image Downloader - Main Entry Point
"""
import asyncio
import logging
from datetime import datetime, timedelta
import yaml
import sys
import os

from downloader import MOSDACDownloader
from scheduler import DownloadScheduler
from utils import setup_logging, load_config

def main():
    """Main function"""
    # Load configuration
    config = load_config()
    
    # Setup logging
    logger = setup_logging(config)
    
    try:
        # Check if running as scheduler or single download
        if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
            logger.info("Starting scheduled downloader")
            scheduler = DownloadScheduler(config)
            scheduler.run()
        else:
            logger.info("Starting single download session")
            downloader = MOSDACDownloader(config)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=config['download']['lookback_days'])
            
            # Run download
            asyncio.run(downloader.download_all_images(start_date, end_date))
            
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
