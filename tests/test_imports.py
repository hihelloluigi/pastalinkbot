print("Testing imports...")

try:
    from config.settings import Settings, load_settings

    print("✅ config.settings - OK")
except ImportError as e:
    print(f"❌ config.settings - MISSING: {e}")

try:
    from config.constants import ConversationState, IntentType

    print("✅ config.constants - OK")
except ImportError as e:
    print(f"❌ config.constants - MISSING: {e}")

try:
    from core.services.catalog import CatalogService

    print("✅ core.services.catalog - OK")
except ImportError as e:
    print(f"❌ core.services.catalog - MISSING: {e}")

try:
    from core.services.validator import InputValidationService

    print("✅ core.services.validator - OK")
except ImportError as e:
    print(f"❌ core.services.validator - MISSING: {e}")

try:
    from core.services.classifier import ClassificationService

    print("✅ core.services.classifier - OK")
except ImportError as e:
    print(f"❌ core.services.classifier - MISSING: {e}")

try:
    from core.services.formatter import ResponseFormatterService

    print("✅ core.services.formatter - OK")
except ImportError as e:
    print(f"❌ core.services.formatter - MISSING: {e}")

try:
    from core.handlers.commands import CommandHandlers

    print("✅ core.handlers.commands - OK")
except ImportError as e:
    print(f"❌ core.handlers.commands - MISSING: {e}")

try:
    from core.handlers.messages import MessageHandlers

    print("✅ core.handlers.messages - OK")
except ImportError as e:
    print(f"❌ core.handlers.messages - MISSING: {e}")

try:
    from core.handlers.conversation import ConversationHandlers

    print("✅ core.handlers.conversation - OK")
except ImportError as e:
    print(f"❌ core.handlers.conversation - MISSING: {e}")

try:
    from utils.logging import LoggerMixin

    print("✅ utils.logging - OK")
except ImportError as e:
    print(f"❌ utils.logging - MISSING: {e}")

try:
    from utils.i18n import get_translator

    print("✅ utils.i18n - OK")
except ImportError as e:
    print(f"❌ utils.i18n - MISSING: {e}")

print("\nIf any modules show as MISSING, create those files first!")
