"""VESTRIK report rendering.

This compatibility-preserving migration reuses the proven CEREBRO renderer
while exposing VESTRIK-native output. No analysis behavior changes here.
"""

import json
import os
from cerebro.report import ReportMixin as _LegacyReportMixin
from . import __version__


class ReportMixin(_LegacyReportMixin):
    """VESTRIK-branded rendering with temporary CEREBRO API compatibility."""

    def export_vestrik_report(self, query: str = None, top_n: int = 10) -> str:
        text = super().export_cerebro_report(query=query, top_n=top_n)
        return text.replace("CEREBRO", "VESTRIK").replace("cerebro", "vestrik")

    def export_cerebro_report(self, query: str = None, top_n: int = 10) -> str:
        """Deprecated compatibility alias. Prefer export_vestrik_report()."""
        return self.export_vestrik_report(query=query, top_n=top_n)

    def export_json(self, output_path: str = None) -> str:
        payload = json.loads(super().export_json())
        payload["vestrik_version"] = payload.pop("cerebro_version", __version__)
        json_str = json.dumps(payload, indent=2, default=str)
        if output_path:
            dirname = os.path.dirname(output_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str
