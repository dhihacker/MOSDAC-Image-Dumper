"""
Scheduler for periodic downloads
"""
import schedule
import time
import asyncio
import logging
from datetime import datetime
import threading

class DownloadScheduler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.running = False
        
    def run_download(self):
        """Run download in a separate thread"""
        from downloader import MOSDACDownloader
        
        async def download():
            downloader = MOSDACDownloader(self.config)
            await downloader.download_latest_only()
        
        # Run in new event loop for thread safety
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(download())
        loop.close()
    
    def job(self):
        """Scheduled job"""
        self.logger.info(f"Running scheduled download at {datetime.now()}")
        
        # Run in separate thread to avoid blocking
        thread = threading.Thread(target=self.run_download)
        thread.start()
        thread.join(timeout=self.config['scheduler']['max_runtime'] * 60)
        
        if thread.is_alive():
            self.logger.warning("Download job timed out")
    
    def run(self):
        """Start the scheduler"""
        self.running = True
        
        # Schedule job
        interval = self.config['scheduler']['interval_minutes']
        schedule.every(interval).minutes.do(self.job)
        
        # Run immediately on start
        self.job()
        
        self.logger.info(f"Scheduler started. Running every {interval} minutes.")
        
        # Keep running
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.logger.info("Scheduler stopped")
