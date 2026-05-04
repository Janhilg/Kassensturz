from core import export_utils


class CashExportService:
    export_excel = staticmethod(export_utils.export_excel)
    export_text = staticmethod(export_utils.export_text)
    export_all = staticmethod(export_utils.export_all)
    import_all_from_excel = staticmethod(export_utils.import_all_from_excel)
