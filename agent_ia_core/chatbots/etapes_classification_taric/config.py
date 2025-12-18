"""
Configuration du chatbot de classification TARIC.
"""

CHATBOT_CONFIG = {
    'name': 'Classification TARIC',
    'description': 'Assistant specialise en classification douaniere TARIC',
    'version': '1.0.0',

    # Parametres du LLM
    'max_iterations': 10,
    'temperature': 0.3,  # Plus deterministe pour classification

    # Tools actives pour ce chatbot
    'tools_enabled': [
        'get_expedition_documents',
        'search_taric_database',
        # 'analyze_product_image',      # TODO: A implementer
        # 'analyze_technical_sheet',    # TODO: A implementer
        # 'validate_taric_code',        # TODO: A implementer
        # 'get_tariff_rates',           # TODO: A implementer
    ],

    # Nombre de codes TARIC a proposer
    'num_candidates': 5,

    # Seuils de confiance
    'confidence_thresholds': {
        'high': 80,      # >= 80% = haute confiance
        'medium': 50,    # >= 50% = confiance moyenne
        'low': 0,        # < 50% = faible confiance
    },

    # Messages par defaut
    'messages': {
        'no_documents': "Je ne vois pas encore de documents. Veuillez telecharger des photos ou fiches techniques dans la section de gauche.",
        'analyzing': "Je procede a l'analyse de vos documents...",
        'error': "Une erreur s'est produite. Veuillez reessayer.",
    }
}
