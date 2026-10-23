import unittest
from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest
from predash.macro import MacroError


class AppWorkspaceIntegration(unittest.TestCase):
    def test_main_app_missing_market_data_and_empty_dashboard(self):
        with patch('predash.public_market.fetch_public_market', return_value={}), patch.dict('os.environ', {'APP_PASSWORD': ''}), patch('predash.macro.fetch_vix', side_effect=MacroError('테스트: 자료 없음')):
            app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=20)
            self.assertFalse(app.exception)
            nav = next(x for x in app.radio if x.key == 'navigation')
            nav.set_value('오늘의 점검').run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any('확인 필요' in e.value for e in app.caption))
            self.assertFalse(any(x.key == 'market_popup_close' for x in app.button))
            next(x for x in app.button if x.key == 'workspace_market_refresh').click().run(timeout=20)
            self.assertFalse(app.exception)

    def test_main_app_risk_modal_without_account_access(self):
        from datetime import date
        def vix(day):return {'date': day.isoformat(), 'close': 35, 'rows': []}
        with patch('predash.public_market.fetch_public_market', return_value={}), patch.dict('os.environ', {'APP_PASSWORD': ''}), patch('predash.macro.fetch_vix', side_effect=vix):
            app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(any(x.key == 'market_popup_close' for x in app.button))
            next(x for x in app.button if x.key == 'market_popup_close').click().run(timeout=20)
            self.assertFalse(app.exception)
            next(x for x in app.radio if x.key == 'navigation').set_value('오늘의 점검').run(timeout=20)
            self.assertFalse(app.exception)
            self.assertFalse(any(x.key == 'market_popup_close' for x in app.button))


if __name__ == '__main__':unittest.main()
