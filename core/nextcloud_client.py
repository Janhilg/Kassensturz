from core import nextcloud_sync


class NextcloudClient:
    get_verify_setting = staticmethod(nextcloud_sync.get_verify_setting)
    nextcloud_configured = staticmethod(nextcloud_sync.nextcloud_configured)
    build_webdav_url = staticmethod(nextcloud_sync.build_webdav_url)
    ensure_nextcloud_folder = staticmethod(nextcloud_sync.ensure_nextcloud_folder)
    download_remote_excel_to_temp = staticmethod(nextcloud_sync.download_remote_excel_to_temp)
    download_remote_excel_if_exists = staticmethod(nextcloud_sync.download_remote_excel_if_exists)
    upload_file_to_nextcloud = staticmethod(nextcloud_sync.upload_file_to_nextcloud)
    upload_excel_file_to_nextcloud = staticmethod(nextcloud_sync.upload_excel_file_to_nextcloud)
    upload_text_file_to_nextcloud = staticmethod(nextcloud_sync.upload_text_file_to_nextcloud)
    upload_files = staticmethod(nextcloud_sync.upload_files)
