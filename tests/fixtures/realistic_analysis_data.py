"""Realistic mock fixtures that match actual API response structure.

These fixtures provide comprehensive, schema-matched mock data based on
real analysis outputs from test_results/ to ensure unit tests validate
the actual data structures the system produces.
"""

from datetime import datetime
from typing import Any


def get_realistic_filing_analysis_response() -> dict[str, Any]:
    """Get comprehensive filing analysis response matching real API output.

    This fixture matches the structure of actual OpenAI API responses
    with 28+ sub-sections across 6 major filing sections.
    """
    return {
        "filing_summary": "Microsoft Corp's 10-K filing reveals strong financial performance driven by significant growth in cloud services and software sales, supported by a robust operational framework and strategic initiatives. The company's diversified portfolio and competitive advantages position it well for future growth, despite facing various industry-specific risks and regulatory challenges. Overall, Microsoft demonstrates a healthy balance sheet and strong cash flow, underscoring its financial stability and commitment to innovation.",
        "executive_summary": "Microsoft Corp continues to showcase its leadership in the technology sector through its comprehensive 10-K filing, which highlights solid operational performance and strategic positioning for future growth. The company has successfully capitalized on the increasing demand for cloud computing and digital solutions, with key products such as Microsoft 365 and Azure driving substantial revenue growth. The Management Discussion & Analysis section emphasizes effective cost management and operational efficiencies, contributing to improved profitability and a healthy liquidity position.\n\nHowever, the filing also acknowledges various risk factors that could impact Microsoft's operations, including regulatory challenges and industry-specific uncertainties. The company's proactive approach to risk management is evident in its strategic initiatives focused on innovation, sustainability, and market expansion. Overall, Microsoft's strong financial metrics, coupled with its commitment to technological advancement and strategic growth initiatives, position it favorably in a competitive landscape, ensuring continued success and shareholder value creation.",
        "key_insights": [
            "Strong revenue growth driven by cloud services and software sales.",
            "Robust demand for Microsoft 365 and Azure contributes significantly to profitability.",
            "Effective cost management has led to improved margins and net income growth.",
            "Healthy liquidity position supports short-term obligations and growth investments.",
            "Diversified portfolio mitigates risks associated with market fluctuations.",
            "Strategic investments in technology and acquisitions enhance competitive advantage.",
            "Proactive risk management strategies address regulatory and operational challenges.",
            "Positive cash flow from operations indicates strong core business performance.",
            "Market conditions favor technology adoption across various industries.",
            "Sustainability initiatives align with global trends and customer expectations.",
        ],
        "financial_highlights": [
            "Revenue growth of 16% year-over-year, primarily from cloud services.",
            "Operating income increased by 23%, reflecting improved margins.",
            "Cash and cash equivalents of $29.5 billion, indicating strong liquidity.",
            "Debt-to-equity ratio remains low at 0.47, showcasing financial stability.",
            "Net income margin improved to 36.7%, driven by effective cost control.",
        ],
        "risk_factors": [
            "Regulatory changes impacting technology operations and data privacy.",
            "Intense competition in the cloud computing market from AWS and Google.",
            "Cybersecurity threats and data privacy concerns affecting customer trust.",
            "Economic downturns affecting enterprise customer spending on software.",
            "Operational challenges related to global supply chain disruptions.",
        ],
        "opportunities": [
            "Expansion of cloud services in emerging markets and new verticals.",
            "Increased adoption of AI and machine learning solutions across enterprises.",
            "Strategic partnerships to enhance product offerings and market reach.",
            "Growth potential in enterprise software solutions and digital transformation.",
            "Investment in sustainability and green technology initiatives for competitive advantage.",
        ],
        "confidence_score": 0.95,
        "section_analyses": [
            {
                "section_name": "Business",
                "section_summary": "The Business section of Microsoft Corp's 10-K filing provides a detailed overview of the company's operations, key products, competitive advantages, strategic initiatives, and performance across various business and geographic segments.",
                "consolidated_insights": [
                    "Microsoft's operational efficiency is supported by extensive infrastructure and innovation focus.",
                    "Key products like Azure and Microsoft 365 are driving significant revenue growth.",
                    "The company leverages strong brand and technology capabilities as competitive advantages.",
                    "Strategic initiatives are centered around cloud services, AI, and sustainability.",
                    "Microsoft's business segments show diversification, reducing dependency on single revenue streams.",
                    "Geographic performance indicates strength in North America with emerging opportunities globally.",
                ],
                "overall_sentiment": 0.85,
                "sub_sections": [
                    {
                        "sub_section_name": "Operational Overview",
                        "schema_type": "OperationalOverview",
                        "processing_time_ms": 1245,
                        "analysis": {
                            "description": "Microsoft operates as a global technology leader providing software, services, devices, and solutions that help people and businesses realize their full potential.",
                            "industry_classification": "Technology Software and Services",
                            "primary_markets": [
                                "Enterprise Software",
                                "Cloud Computing",
                                "Gaming",
                                "Productivity Software",
                            ],
                            "target_customers": [
                                "Enterprise businesses",
                                "Small and medium businesses",
                                "Individual consumers",
                                "Government organizations",
                            ],
                            "business_model": "Subscription-based software-as-a-service with device sales and gaming services",
                            "operational_scale": "Global operations in over 190 countries with 221,000+ employees",
                            "key_infrastructure": [
                                "Azure cloud platform",
                                "Global data centers",
                                "AI and machine learning capabilities",
                                "Microsoft 365 ecosystem",
                            ],
                        },
                    },
                    {
                        "sub_section_name": "Key Product: Microsoft 365",
                        "schema_type": "KeyProduct",
                        "processing_time_ms": 890,
                        "analysis": {
                            "product_name": "Microsoft 365",
                            "description": "Comprehensive productivity and collaboration suite including Office applications, Teams, SharePoint, and security features",
                            "market_position": "Market leader in enterprise productivity software",
                            "revenue_contribution": "Significant contributor to Productivity and Business Processes segment",
                            "strategic_importance": "Core platform for digital transformation and hybrid work solutions",
                            "competitive_advantages": [
                                "Integrated ecosystem",
                                "Enterprise security",
                                "AI-powered features",
                                "Global scale",
                            ],
                            "growth_outlook": "Strong growth driven by digital transformation and remote work trends",
                        },
                    },
                    {
                        "sub_section_name": "Competitive Advantage Analysis",
                        "schema_type": "CompetitiveAdvantage",
                        "processing_time_ms": 1156,
                        "analysis": {
                            "core_advantages": [
                                "Comprehensive product ecosystem",
                                "Strong brand recognition",
                                "Global scale and reach",
                                "Innovation capabilities",
                            ],
                            "key_differentiators": "Integrated platform approach combining productivity, cloud, and AI capabilities",
                            "market_position": "Dominant position in enterprise software with growing cloud market share",
                            "competitor_analysis": {
                                "AWS": "Strong in infrastructure but Microsoft leads in integrated enterprise solutions",
                                "Google": "Competitive in AI and productivity but Microsoft has stronger enterprise presence",
                                "Oracle": "Strong in database but Microsoft has broader platform capabilities",
                            },
                            "sustainability_assessment": "Strong competitive moat through platform network effects and switching costs",
                            "innovation_pipeline": "Significant investments in AI, quantum computing, and mixed reality technologies",
                        },
                    },
                ],
            },
            {
                "section_name": "Risk Factors",
                "section_summary": "Microsoft faces various operational, regulatory, and market risks that could impact business performance and growth prospects.",
                "consolidated_insights": [
                    "Regulatory compliance costs and constraints pose ongoing operational challenges.",
                    "Intense competition in cloud computing market pressures pricing and margins.",
                    "Cybersecurity threats require continuous investment in defensive capabilities.",
                    "Economic downturns could reduce enterprise technology spending.",
                    "Global supply chain disruptions may affect hardware business operations.",
                ],
                "overall_sentiment": -0.2,
                "sub_sections": [
                    {
                        "sub_section_name": "Regulatory Risk Assessment",
                        "schema_type": "RegulatoryRisk",
                        "processing_time_ms": 1034,
                        "analysis": {
                            "risk_description": "Increased regulatory scrutiny and compliance requirements across global markets",
                            "regulatory_domains": [
                                "Data privacy (GDPR, CCPA)",
                                "Antitrust regulations",
                                "Digital services taxes",
                                "AI governance",
                            ],
                            "compliance_requirements": "Extensive compliance programs for data protection, competition law, and emerging AI regulations",
                            "potential_penalties": "Significant fines and operational restrictions possible for non-compliance",
                            "geographic_scope": "Global regulatory exposure with particular focus on EU, US, and Asia-Pacific markets",
                            "enforcement_risk": "High enforcement activity from regulators in key markets",
                            "regulatory_changes": "Evolving AI governance frameworks and digital platform regulations",
                            "mitigation_strategies": [
                                "Dedicated compliance teams",
                                "Regulatory monitoring systems",
                                "Proactive engagement with regulators",
                            ],
                            "impact_timeline": "Ongoing with increasing intensity over next 2-3 years",
                        },
                    },
                    {
                        "sub_section_name": "Market Competition Risk",
                        "schema_type": "IndustryRisk",
                        "processing_time_ms": 967,
                        "analysis": {
                            "risk_description": "Intense competition in cloud computing and enterprise software markets",
                            "market_volatility": "Rapid technology changes and evolving customer preferences",
                            "competitive_pressures": "Pricing pressure from AWS, Google Cloud, and emerging AI-first competitors",
                            "disruption_threats": [
                                "AI-native startups",
                                "Open source alternatives",
                                "Platform consolidation",
                            ],
                            "market_saturation": "Maturing enterprise software market with slowing growth rates",
                            "innovation_risks": "Need for continuous R&D investment to maintain competitive position",
                            "customer_concentration": "Dependence on large enterprise customers for significant revenue",
                        },
                    },
                ],
            },
        ],
        "total_processing_time_ms": 46021,
        "total_sections_analyzed": 6,
        "total_sub_sections_analyzed": 28,
        "analysis_timestamp": "2025-07-19T10:13:41.186250+00:00",
    }


def get_realistic_section_analysis_response() -> dict[str, Any]:
    """Get realistic individual section analysis response."""
    return {
        "section_name": "Item 1 - Business",
        "section_summary": "Comprehensive analysis of Microsoft's business operations, competitive position, and strategic initiatives across global markets.",
        "consolidated_insights": [
            "Microsoft maintains strong competitive advantages through integrated product ecosystem",
            "Cloud services represent the primary growth driver for future revenue expansion",
            "AI integration across product portfolio creates sustainable differentiation",
            "Global operational scale provides resilience and market reach advantages",
        ],
        "overall_sentiment": 0.9,
        "critical_findings": [
            "Azure revenue growth of 30% demonstrates market leadership in cloud computing",
            "Microsoft 365 adoption accelerated by remote work trends",
            "Strategic acquisitions enhance AI and gaming capabilities",
        ],
        "sub_sections": [
            {
                "sub_section_name": "Operational Overview",
                "schema_type": "OperationalOverview",
                "processing_time_ms": 1245,
                "analysis": {
                    "description": "Microsoft operates as a global technology leader in software, services, devices, and solutions",
                    "industry_classification": "Technology Software and Services",
                    "primary_markets": [
                        "Enterprise Software",
                        "Cloud Computing",
                        "Gaming",
                        "Productivity Software",
                    ],
                    "target_customers": [
                        "Enterprise businesses",
                        "SMBs",
                        "Individual consumers",
                        "Government",
                    ],
                    "business_model": "Subscription-based SaaS with device sales and gaming services",
                    "operational_scale": "Global operations in 190+ countries with 221,000+ employees",
                },
            }
        ],
    }


def get_realistic_edgar_filing_sections() -> dict[str, str]:
    """Get realistic filing sections matching actual SEC filing content."""
    return {
        "Item 1 - Business": """Microsoft Corporation develops, licenses, and supports a wide range of software products, services, and devices. Our products include operating systems; cross-device productivity applications; server applications; business solution applications; desktop and server management tools; software development tools; and video games. We also design and sell hardware including PCs, tablets, gaming and entertainment consoles, other intelligent devices, and related accessories.

Our mission is to empower every person and every organization on the planet to achieve more. Our strategy is to build best-in-class platforms and productivity services for an intelligent cloud and an intelligent edge infused with artificial intelligence (AI).

We create technology that transforms the way people work, play, and communicate across every device and platform. We develop and market software, hardware, and services designed to deliver new opportunities, greater convenience, and enhanced value to people's lives.

SEGMENTS

We operate in three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.

Productivity and Business Processes: Our Productivity and Business Processes segment consists of products and services in our portfolio of productivity, communication, and information services, spanning a variety of devices and platforms. This segment primarily comprises:

• Office Commercial products and services, including volume licensing of the Office suite to businesses, government, and academic institutions
• Office Consumer services, including Office 365 subscriptions for individual consumers
• Microsoft Teams, our collaboration and communication platform
• Exchange, SharePoint, OneDrive, Skype for Business, and Microsoft Viva""",
        "Item 1A - Risk Factors": """Our business faces a wide variety of risks, many of which are inherent in our business. The risks described below may materially and adversely affect our business, financial condition, results of operations, cash flows, and the trading price of our common stock.

COMPETITIVE FACTORS

The software industry is intensely competitive and subject to rapid technological change. Our competitors range from large, well-established companies to small, specialized firms. They include:

• Companies that provide competing platforms, applications, and services, including Amazon, Apple, Google, IBM, Oracle, Salesforce, and others
• Hardware manufacturers that may optimize their products for competing software platforms or create competing software platforms
• Open source software companies and projects
• Companies developing AI and machine learning capabilities

We face significant competition across all markets for our products and services. Competitive factors include pricing, performance, ease of use, product features, customer service, and the ability to offer comprehensive solutions.

CYBERSECURITY AND DATA PRIVACY

Security of our products and services is important to our customers. Threats to IT security can take a variety of forms. Individual and groups of hackers, possible state-sponsored organizations, and sophisticated malware and viruses present threats that may harm our business in a variety of ways including:

• Product and service security vulnerabilities could lead to reduced revenue, increased costs, liability claims, or harm to our reputation or competitive position
• Our enterprise services handle large amounts of sensitive data that could be compromised
• Cyberattacks on our infrastructure could disrupt business operations""",
        "Item 7 - Management Discussion & Analysis": """FISCAL YEAR 2024 COMPARED WITH FISCAL YEAR 2023

Revenue increased $21.5 billion or 16% driven by growth across all our segments. Productivity and Business Processes revenue increased driven by Office 365 Commercial and Microsoft Teams growth. Intelligent Cloud revenue increased driven by Azure and other cloud services growth of 30%. More Personal Computing revenue increased driven by growth in Windows Commercial, Devices, Xbox content and services, and Search and news advertising.

Operating income increased $22.6 billion or 23% driven by the revenue growth noted above, offset in part by an increase in operating expenses.

PRODUCTIVITY AND BUSINESS PROCESSES

Revenue increased $8.4 billion or 13% driven by Office 365 Commercial growth. Office 365 Commercial revenue grew 15% driven by seat growth across customer segments and higher revenue per user from premium offerings including Microsoft Teams, advanced security, and compliance features.

Microsoft Teams revenue growth was driven by growth in seat count and increased usage resulting from continued hybrid work adoption.

INTELLIGENT CLOUD

Revenue increased $9.5 billion or 21% driven by Azure and other cloud services growth. Azure revenue grew 30% driven by increased consumption from existing customers and continued customer acquisition across all customer sizes and geographies.

SQL Server revenue growth was driven by continued hybrid demand and Premium tier uptake.

MORE PERSONAL COMPUTING

Revenue increased $3.6 billion or 17% driven by growth across Windows, Devices, Xbox, and Search advertising. Windows Commercial revenue grew driven by the commercial PC market and increased adoption of Windows 11.""",
    }


def get_realistic_company_data() -> dict[str, Any]:
    """Get realistic company data matching Edgar API responses."""
    return {
        "cik": 789019,
        "name": "Microsoft Corporation",
        "ticker": "MSFT",
        "sic_code": "7372",
        "sic_description": "Services-Prepackaged Software",
        "industry": "Technology",
        "sector": "Information Technology",
        "address": {
            "street1": "One Microsoft Way",
            "city": "Redmond",
            "state": "WA",
            "zip": "98052-6399",
            "country": "United States",
        },
        "phone": "425-882-8080",
        "website": "https://www.microsoft.com",
        "fiscal_year_end": "June 30",
        "exchange": "NASDAQ",
        "market_cap": 2800000000000,  # $2.8T
        "shares_outstanding": 7400000000,
    }


def get_realistic_filing_metadata() -> dict[str, Any]:
    """Get realistic filing metadata matching Edgar API responses."""
    return {
        "accession_number": "0001564590-24-000029",
        "filing_date": "2024-07-30",
        "acceptance_datetime": "2024-07-30T16:03:04.000Z",
        "period_of_report": "2024-06-30",
        "form_type": "10-K",
        "file_number": "001-37845",
        "film_number": "241092907",
        "is_inline_xbrl": True,
        "document_count": 143,
        "size": 15847392,
        "fiscal_year": 2024,
        "fiscal_period": "FY",
    }


def get_processing_metadata() -> dict[str, Any]:
    """Get realistic processing metadata."""
    return {
        "total_processing_time_ms": 46021,
        "total_sections_analyzed": 6,
        "total_sub_sections_analyzed": 28,
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "llm_provider": "OpenAI",
        "llm_model": "gpt-4o-mini",
        "confidence_score": 0.95,
        "analysis_version": "1.0.0",
    }
