"""
Tool pour rechercher dans la base de donnees TARIC.
Version basique - sera amelioree avec une vraie base de donnees.
"""
from typing import Dict, Any, List


# Base de donnees simplifiee des codes TARIC courants
# A remplacer par une vraie base de donnees ou API
TARIC_DATABASE = {
    # Chapitre 84 - Machines et appareils mecaniques
    '8471300000': {
        'code_taric': '8471300000',
        'code_nc': '84713000',
        'code_sh': '847130',
        'description': 'Machines automatiques de traitement de l\'information, portables, d\'un poids <= 10 kg',
        'keywords': ['ordinateur', 'portable', 'laptop', 'notebook', 'pc portable'],
        'chapter': '84',
        'section': 'XVI'
    },
    '8471410000': {
        'code_taric': '8471410000',
        'code_nc': '84714100',
        'code_sh': '847141',
        'description': 'Autres machines automatiques de traitement de l\'information comprenant dans la meme enveloppe au moins une unite centrale et une unite d\'entree/sortie',
        'keywords': ['ordinateur', 'bureau', 'desktop', 'pc', 'tour'],
        'chapter': '84',
        'section': 'XVI'
    },
    '8471490000': {
        'code_taric': '8471490000',
        'code_nc': '84714900',
        'code_sh': '847149',
        'description': 'Autres machines automatiques de traitement de l\'information presentees sous forme de systemes',
        'keywords': ['serveur', 'systeme', 'informatique'],
        'chapter': '84',
        'section': 'XVI'
    },
    '8473300000': {
        'code_taric': '8473300000',
        'code_nc': '84733000',
        'code_sh': '847330',
        'description': 'Parties et accessoires des machines du n 84.71',
        'keywords': ['accessoire', 'piece', 'composant', 'informatique'],
        'chapter': '84',
        'section': 'XVI'
    },
    '8542310000': {
        'code_taric': '8542310000',
        'code_nc': '85423100',
        'code_sh': '854231',
        'description': 'Processeurs et controleurs, meme combines avec des memoires',
        'keywords': ['processeur', 'cpu', 'controleur', 'puce'],
        'chapter': '85',
        'section': 'XVI'
    },
    # Chapitre 85 - Machines et appareils electriques
    '8517120000': {
        'code_taric': '8517120000',
        'code_nc': '85171200',
        'code_sh': '851712',
        'description': 'Telephones pour reseaux cellulaires ou pour autres reseaux sans fil',
        'keywords': ['telephone', 'mobile', 'smartphone', 'cellulaire'],
        'chapter': '85',
        'section': 'XVI'
    },
    '8528720000': {
        'code_taric': '8528720000',
        'code_nc': '85287200',
        'code_sh': '852872',
        'description': 'Autres appareils recepteurs de television, en couleurs',
        'keywords': ['television', 'tv', 'ecran', 'moniteur'],
        'chapter': '85',
        'section': 'XVI'
    },
    # Chapitre 61 - Vetements
    '6109100000': {
        'code_taric': '6109100000',
        'code_nc': '61091000',
        'code_sh': '610910',
        'description': 'T-shirts et maillots de corps, en bonneterie, de coton',
        'keywords': ['t-shirt', 'tshirt', 'maillot', 'coton', 'vetement'],
        'chapter': '61',
        'section': 'XI'
    },
    '6203420000': {
        'code_taric': '6203420000',
        'code_nc': '62034200',
        'code_sh': '620342',
        'description': 'Pantalons, salopettes, culottes et shorts, de coton, pour hommes ou garconnets',
        'keywords': ['pantalon', 'jean', 'coton', 'homme', 'vetement'],
        'chapter': '62',
        'section': 'XI'
    },
    # Chapitre 64 - Chaussures
    '6403990000': {
        'code_taric': '6403990000',
        'code_nc': '64039900',
        'code_sh': '640399',
        'description': 'Autres chaussures a dessus en cuir naturel',
        'keywords': ['chaussure', 'cuir', 'soulier'],
        'chapter': '64',
        'section': 'XII'
    },
    '6404110000': {
        'code_taric': '6404110000',
        'code_nc': '64041100',
        'code_sh': '640411',
        'description': 'Chaussures de sport a dessus en matieres textiles',
        'keywords': ['basket', 'sneaker', 'sport', 'chaussure', 'textile'],
        'chapter': '64',
        'section': 'XII'
    },
}


def search_taric_database(
    keywords: List[str] = None,
    product_description: str = None,
    code_prefix: str = None
) -> Dict[str, Any]:
    """
    Recherche dans la base TARIC des codes correspondant aux criteres.

    Args:
        keywords: Liste de mots-cles de recherche
        product_description: Description complete du produit
        code_prefix: Prefixe de code TARIC pour filtrer

    Returns:
        Dict avec les resultats de recherche
    """
    try:
        results = []
        search_terms = []

        # Collecter les termes de recherche
        if keywords:
            search_terms.extend([k.lower() for k in keywords])

        if product_description:
            # Extraire les mots significatifs de la description
            words = product_description.lower().split()
            search_terms.extend([w for w in words if len(w) > 3])

        if not search_terms and not code_prefix:
            return {
                'success': False,
                'error': "Veuillez fournir des mots-cles ou une description",
                'results': [],
                'count': 0
            }

        # Rechercher dans la base
        for code, data in TARIC_DATABASE.items():
            score = 0

            # Filtrer par prefixe si fourni
            if code_prefix and not code.startswith(code_prefix):
                continue

            # Calculer le score de pertinence
            for term in search_terms:
                # Verifier dans les keywords
                for kw in data.get('keywords', []):
                    if term in kw or kw in term:
                        score += 10

                # Verifier dans la description
                if term in data.get('description', '').lower():
                    score += 5

            if score > 0:
                results.append({
                    'code_taric': data['code_taric'],
                    'code_nc': data['code_nc'],
                    'code_sh': data['code_sh'],
                    'description': data['description'],
                    'chapter': data.get('chapter', ''),
                    'section': data.get('section', ''),
                    'relevance_score': score
                })

        # Trier par score de pertinence
        results.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Limiter aux 10 premiers resultats
        results = results[:10]

        return {
            'success': True,
            'search_terms': search_terms,
            'results': results,
            'count': len(results),
            'message': f"{len(results)} code(s) TARIC trouve(s)"
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'results': [],
            'count': 0
        }


def get_taric_code_details(code: str) -> Dict[str, Any]:
    """
    Obtenir les details d'un code TARIC specifique.

    Args:
        code: Code TARIC (10 chiffres)

    Returns:
        Dict avec les details du code
    """
    # Normaliser le code
    code = code.replace('.', '').replace(' ', '')

    if code in TARIC_DATABASE:
        data = TARIC_DATABASE[code]
        return {
            'success': True,
            'found': True,
            **data
        }

    return {
        'success': True,
        'found': False,
        'message': f"Code TARIC {code} non trouve dans la base locale"
    }


# Definition de la tool pour le registry
TOOL_DEFINITION = {
    'name': 'search_taric_database',
    'description': (
        "Rechercher dans la base de donnees TARIC des codes correspondant "
        "a la description du produit. Retourne les codes les plus pertinents "
        "avec leur description et score de pertinence."
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'keywords': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': "Mots-cles de recherche (ex: ['ordinateur', 'portable'])"
            },
            'product_description': {
                'type': 'string',
                'description': "Description complete du produit"
            },
            'code_prefix': {
                'type': 'string',
                'description': "Prefixe de code pour filtrer (ex: '84' pour chapitre 84)"
            }
        },
        'required': []
    },
    'function': search_taric_database,
    'category': 'classification'
}
