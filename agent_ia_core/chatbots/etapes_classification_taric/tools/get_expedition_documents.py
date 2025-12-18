"""
Tool pour recuperer les documents d'une expedition.
"""
from typing import Dict, Any, Optional


def get_expedition_documents(
    expedition_id: int,
    type_filter: str = "all",
    user=None
) -> Dict[str, Any]:
    """
    Recupere la liste des documents (photos et fiches techniques)
    telecharges pour une expedition.

    Args:
        expedition_id: ID de l'expedition
        type_filter: Filtrer par type ("all", "photo", "fiche_technique")
        user: Django User pour verification des permissions

    Returns:
        Dict avec les documents disponibles
    """
    try:
        from apps.expeditions.models import Expedition, ExpeditionDocument

        # Recuperer l'expedition
        expedition = Expedition.objects.filter(pk=expedition_id).first()
        if not expedition:
            return {
                'success': False,
                'error': f"Expedition {expedition_id} non trouvee",
                'photos': [],
                'fiches_techniques': [],
                'total': 0
            }

        # Verifier les permissions si user fourni
        if user and expedition.user_id != user.id:
            return {
                'success': False,
                'error': "Acces non autorise a cette expedition",
                'photos': [],
                'fiches_techniques': [],
                'total': 0
            }

        # Recuperer les documents
        photos = []
        fiches_techniques = []

        if type_filter in ('all', 'photo'):
            photo_docs = expedition.documents.filter(type='photo').order_by('ordre', '-created_at')
            photos = [
                {
                    'id': doc.id,
                    'nom': doc.nom_original,
                    'url': doc.fichier.url if doc.fichier else None,
                    'uploaded_at': doc.created_at.isoformat() if doc.created_at else None,
                    'is_image': doc.is_image
                }
                for doc in photo_docs
            ]

        if type_filter in ('all', 'fiche_technique'):
            fiche_docs = expedition.documents.filter(type='fiche_technique').order_by('ordre', '-created_at')
            fiches_techniques = [
                {
                    'id': doc.id,
                    'nom': doc.nom_original,
                    'url': doc.fichier.url if doc.fichier else None,
                    'uploaded_at': doc.created_at.isoformat() if doc.created_at else None,
                    'is_pdf': doc.nom_original.lower().endswith('.pdf') if doc.nom_original else False
                }
                for doc in fiche_docs
            ]

        return {
            'success': True,
            'expedition_id': expedition_id,
            'expedition_reference': expedition.reference,
            'product_name': expedition.nom_article or 'Non specifie',
            'photos': photos,
            'fiches_techniques': fiches_techniques,
            'total': len(photos) + len(fiches_techniques),
            'summary': f"{len(photos)} photo(s), {len(fiches_techniques)} fiche(s) technique(s)"
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'photos': [],
            'fiches_techniques': [],
            'total': 0
        }


# Definition de la tool pour le registry (si utilise avec le systeme global)
TOOL_DEFINITION = {
    'name': 'get_expedition_documents',
    'description': (
        "Recuperer la liste des documents (photos et fiches techniques) "
        "telecharges par l'utilisateur pour cette expedition. "
        "Utilise cette tool pour voir quels documents sont disponibles avant de les analyser."
    ),
    'parameters': {
        'type': 'object',
        'properties': {
            'expedition_id': {
                'type': 'integer',
                'description': "ID de l'expedition"
            },
            'type_filter': {
                'type': 'string',
                'enum': ['all', 'photo', 'fiche_technique'],
                'description': "Filtrer par type de document (defaut: all)"
            }
        },
        'required': ['expedition_id']
    },
    'function': get_expedition_documents,
    'category': 'classification'
}
