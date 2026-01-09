# Schema de Base de Donnees - Procedures Douanieres

**Version:** 2.0.0
**Date:** Janvier 2026

---

## Vue d'ensemble

Ce document decrit la structure de la base de donnees pour le systeme de procedures douanieres.

```
User (1) --> (N) Expedition (1) --> (5) ExpeditionEtape
                                          |
                                    +-----+-----+
                                    |     |     |
                                    v     v     v
                              Classification  Documents  Expedition
                              Data (1:1)      Data (1:1) Document (1:N)
```

---

## Tables

### 1. Expedition

Table principale representant une expedition douaniere.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Identifiant unique |
| reference | CharField(50) | UNIQUE | Reference (EXP-2025-001) |
| nom_article | CharField(255) | NOT NULL | Nom du produit |
| description | TextField | NULL | Description detaillee |
| direction | CharField(10) | NOT NULL | FR_DZ ou DZ_FR |
| statut | CharField(20) | NOT NULL | brouillon/en_cours/termine/erreur |
| etape_courante | IntegerField | DEFAULT 1 | Etape actuelle (1-5) |
| user_id | ForeignKey | NOT NULL | -> User |
| created_at | DateTimeField | AUTO | Date de creation |
| updated_at | DateTimeField | AUTO | Date de modification |

**Relations:**
- user -> auth.User (N:1)
- etapes <- ExpeditionEtape (1:5)

---

### 2. ExpeditionEtape

Table intermediaire contenant les champs communs a toutes les etapes.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Identifiant unique |
| expedition_id | ForeignKey | NOT NULL | -> Expedition |
| numero | IntegerField | NOT NULL | 1-5 |
| type_etape | CharField(20) | NOT NULL | classification/documents/transmission/paiement/oea |
| statut | CharField(20) | NOT NULL | en_attente/en_cours/termine/erreur |
| completed_at | DateTimeField | NULL | Date de completion |
| created_at | DateTimeField | AUTO | Date de creation |
| updated_at | DateTimeField | AUTO | Date de modification |

**Contrainte unique:** (expedition_id, numero)

**Relations:**
- expedition -> Expedition (N:1)
- classification_data <- ClassificationData (1:1, si numero=1)
- documents_data <- DocumentsData (1:1, si numero=2)
- documents <- ExpeditionDocument (1:N)

---

### 3. ClassificationData

Donnees specifiques a l'etape 1: Classification Douaniere.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Identifiant unique |
| etape_id | OneToOneField | UNIQUE, NOT NULL | -> ExpeditionEtape |
| code_sh | CharField(6) | NULL | Code SH (6 chiffres) |
| code_nc | CharField(8) | NULL | Code NC (8 chiffres) |
| code_taric | CharField(10) | NULL | Code TARIC (10 chiffres) |
| chat_historique | JSONField | DEFAULT [] | Historique du chat |
| propositions | JSONField | DEFAULT [] | Propositions TARIC |
| proposition_selectionnee | IntegerField | NULL | Index de la proposition choisie |

**Format chat_historique:**
```json
[
  {
    "role": "user|assistant|system",
    "content": "Message content",
    "timestamp": "2025-12-18T10:30:00Z"
  }
]
```

**Format propositions:**
```json
[
  {
    "code_sh": "847130",
    "code_nc": "84713000",
    "code_taric": "8471300000",
    "probability": 85,
    "description": "Machines automatiques de traitement...",
    "justification": "Base sur l'analyse..."
  }
]
```

---

### 4. DocumentsData

Donnees specifiques a l'etape 2: Generation de Documents.

**Plus de 50 champs** pour les informations commerciales :

| Categorie | Champs |
|-----------|--------|
| Destinataire | consignee_name, consignee_address, consignee_city, consignee_country, consignee_tax_id |
| Transport | transport_mode, vessel_name, port_of_loading, port_of_discharge |
| Valeurs | fob_value, freight_cost, insurance_cost, cif_value (auto) |
| Marchandises | number_of_packages, gross_weight_kg, net_weight_kg |
| Incoterms | incoterm (EXW, FOB, CIF, DAP...) |
| Statut | dau_genere, d10_genere, d12_genere |

---

### 5. ExpeditionDocument

Documents associes a une etape.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | |
| etape_id | ForeignKey | NOT NULL | -> ExpeditionEtape |
| type | CharField(30) | NOT NULL | photo/fiche_technique/dau/d10/d12/etc |
| fichier | FileField | NOT NULL | Chemin du fichier |
| nom_original | CharField(255) | NOT NULL | Nom original |
| ordre | IntegerField | DEFAULT 0 | Ordre d'affichage |
| created_at | DateTimeField | AUTO | Date de creation |

**Types de documents:**
- photo - Photo du produit
- fiche_technique - Fiche technique PDF
- dau - Document Administratif Unique
- d10 - Formulaire D10
- d12 - Formulaire D12
- certificat_origine - Certificat d'origine

---

## Structure des Fichiers Media

```
data/
+-- db.sqlite3
+-- media_expediciones/
    +-- {expedition_id}/
        +-- etape_1_classification/
        |   +-- images/
        |   |   +-- photo_001.jpg
        |   +-- documents/
        |       +-- fiche_technique.pdf
        |
        +-- etape_2_documents/
            +-- documents/
                +-- dau.pdf
                +-- d10.pdf
```

---

## Diagramme Entite-Relation

```
+------------------+
|      User        |
+--------+---------+
         | 1:N
         v
+------------------+
|    Expedition    |
|------------------|
| reference        |
| nom_article      |
| direction        |
| statut           |
| etape_courante   |
+--------+---------+
         | 1:5
         v
+------------------+
| ExpeditionEtape  |
|------------------|
| numero (1-5)     |
| type_etape       |
| statut           |
+--------+---------+
         |
    +----+----+------------+
    | 1:1     | 1:1        | 1:N
    v         v            v
+--------+ +--------+ +------------------+
|Classif.| |Docs    | |ExpeditionDocument|
|Data    | |Data    | |------------------|
|--------| |--------| | type             |
|code_sh | |consig. | | fichier          |
|code_nc | |transp. | | nom_original     |
|code_   | |valeurs | +------------------+
|taric   | +--------+
|chat_   |
|histor. |
|propos. |
+--------+
```

---

**Version:** 2.0.0
**Derniere mise a jour:** Janvier 2026
