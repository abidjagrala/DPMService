from .models import CompanyInfo


def company_info(request):
    """Add CompanyInfo singleton to all template contexts."""
    return {'company': CompanyInfo.get_instance()}
