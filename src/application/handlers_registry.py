"""Handler registry for registering all command and query handlers with the dispatcher."""

import logging

from src.application.base.dispatcher import Dispatcher
from src.application.handlers.commands.analyze_filing_handler import (
    AnalyzeFilingCommandHandler,
)
from src.application.handlers.commands.import_filings_handler import (
    ImportFilingsCommandHandler,
)
from src.application.handlers.queries.get_analysis_handler import (
    GetAnalysisQueryHandler,
)
from src.application.handlers.queries.get_company_query_handler import (
    GetCompanyQueryHandler,
)
from src.application.handlers.queries.get_filing_handler import (
    GetFilingQueryHandler,
)
from src.application.handlers.queries.get_templates_handler import (
    GetTemplatesQueryHandler,
)
from src.application.handlers.queries.list_analyses_handler import (
    ListAnalysesQueryHandler,
)
from src.application.handlers.queries.list_company_filings_handler import (
    ListCompanyFilingsQueryHandler,
)
from src.application.handlers.queries.search_filings_handler import (
    SearchFilingsHandler,
)

logger = logging.getLogger(__name__)


def register_handlers(dispatcher: Dispatcher) -> None:
    """Register all command and query handlers with the dispatcher.

    This function centralizes handler registration to ensure all handlers
    are properly configured with the CQRS dispatcher.

    Args:
        dispatcher: The CQRS dispatcher to register handlers with
    """
    # Register command handlers
    logger.info("Registering command handlers")
    dispatcher.register_command_handler(AnalyzeFilingCommandHandler)
    dispatcher.register_command_handler(ImportFilingsCommandHandler)

    # Register query handlers
    logger.info("Registering query handlers")
    dispatcher.register_query_handler(GetAnalysisQueryHandler)
    dispatcher.register_query_handler(GetCompanyQueryHandler)
    dispatcher.register_query_handler(GetFilingQueryHandler)
    dispatcher.register_query_handler(ListAnalysesQueryHandler)
    dispatcher.register_query_handler(ListCompanyFilingsQueryHandler)
    dispatcher.register_query_handler(SearchFilingsHandler)
    dispatcher.register_query_handler(GetTemplatesQueryHandler)

    logger.info("Handler registration completed successfully")


def get_configured_dispatcher() -> Dispatcher:
    """Get a dispatcher with all handlers registered.

    This is a convenience function for creating a fully configured
    dispatcher with all application handlers registered.

    Returns:
        Dispatcher with all handlers registered
    """
    dispatcher = Dispatcher()
    register_handlers(dispatcher)
    return dispatcher
