"""Test paketi — testler sırasında log gürültüsünü azalt."""
from bistrobot.logging_utils.logger import configure_logging

# Testlerde yalnızca hataları göster.
configure_logging(level="ERROR")
