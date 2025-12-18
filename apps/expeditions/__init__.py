# apps/expeditions - Module de gestion des expéditions douanières
#
# Structure du module:
#
# expeditions/
# ├── __init__.py          # Ce fichier
# ├── apps.py              # Configuration Django
# ├── models.py            # Modèles: Expedition, ExpeditionEtape, ExpeditionDocument
# ├── views.py             # Vues principales (List, Create, Detail, Delete)
# ├── urls.py              # URLs du module
# ├── forms.py             # Formulaire ExpeditionForm
# ├── admin.py             # Administration Django
# │
# └── etapes/              # Modules par étape du processus douanier
#     ├── __init__.py
#     │
#     ├── classification/  # Étape 1: Classification Douanière (SH/NC/TARIC)
#     │   ├── __init__.py
#     │   ├── views.py
#     │   ├── forms.py
#     │   ├── services.py
#     │   └── urls.py
#     │
#     ├── documents/       # Étape 2: Génération des Documents (DAU, D10, D12)
#     │   ├── __init__.py
#     │   ├── views.py
#     │   └── urls.py
#     │
#     ├── transmission/    # Étape 3: Transmission Électronique (DELTA, BADR)
#     │   ├── __init__.py
#     │   ├── views.py
#     │   └── urls.py
#     │
#     ├── paiement/        # Étape 4: Calcul et Paiement des Droits
#     │   ├── __init__.py
#     │   ├── views.py
#     │   └── urls.py
#     │
#     └── oea/             # Étape 5: Gestion OEA (Opérateur Économique Agréé)
#         ├── __init__.py
#         ├── views.py
#         └── urls.py
