# Schema de Base de Datos - Procedures Douanieres

**Version:** 2.0.0
**Date:** Decembre 2025
**Auteur:** Adrian Ubeda Touati

---

## Vue d'ensemble

Ce document decrit la structure de la base de donnees pour le systeme de procedures douanieres.
L'architecture est basee sur une structure hierarchique:

```
Expedition (1) ────► (5) ExpeditionEtape (table intermediaire)
                              │
                              │ 1:1 (selon type_etape)
                              │
                    ┌─────────┼─────────┬─────────────┬─────────────┐
                    ▼         ▼         ▼             ▼             ▼
             Classification  Documents  Transmission  Paiement     OEA
             Data            Data       Data          Data         Data
                    │
                    │ 1:N
                    ▼
             ExpeditionDocument
```

---

## Tables

### 1. Expedition

Table principale representant une expedition douaniere.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | Identifiant unique |
| `reference` | CharField(50) | UNIQUE | Reference (EXP-2025-001) |
| `nom_article` | CharField(255) | NOT NULL | Nom du produit |
| `description` | TextField | NULL | Description detaillee |
| `direction` | CharField(10) | NOT NULL | FR_DZ ou DZ_FR |
| `statut` | CharField(20) | NOT NULL | brouillon/en_cours/termine/erreur |
| `etape_courante` | IntegerField | DEFAULT 1 | Etape actuelle (1-5) |
| `user_id` | ForeignKey | NOT NULL | → User |
| `created_at` | DateTimeField | AUTO | Date de creation |
| `updated_at` | DateTimeField | AUTO | Date de modification |

**Relations:**
- `user` → `auth.User` (N:1)
- `etapes` ← `ExpeditionEtape` (1:5)

---

### 2. ExpeditionEtape

Table intermediaire contenant les champs communs a toutes les etapes.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | Identifiant unique |
| `expedition_id` | ForeignKey | NOT NULL | → Expedition |
| `numero` | IntegerField | NOT NULL | 1-5 |
| `type_etape` | CharField(20) | NOT NULL | classification/documents/transmission/paiement/oea |
| `statut` | CharField(20) | NOT NULL | en_attente/en_cours/termine/erreur |
| `completed_at` | DateTimeField | NULL | Date de completion |
| `created_at` | DateTimeField | AUTO | Date de creation |
| `updated_at` | DateTimeField | AUTO | Date de modification |

**Contrainte unique:** `(expedition_id, numero)`

**Relations:**
- `expedition` → `Expedition` (N:1)
- `classification_data` ← `ClassificationData` (1:1, si numero=1)
- `documents_data` ← `DocumentsData` (1:1, si numero=2)
- `transmission_data` ← `TransmissionData` (1:1, si numero=3)
- `paiement_data` ← `PaiementData` (1:1, si numero=4)
- `oea_data` ← `OEAData` (1:1, si numero=5)
- `documents` ← `ExpeditionDocument` (1:N)

---

### 3. ClassificationData

Donnees specifiques a l'etape 1: Classification Douaniere.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | Identifiant unique |
| `etape_id` | OneToOneField | UNIQUE, NOT NULL | → ExpeditionEtape |
| `code_sh` | CharField(6) | NULL | Code SH (6 chiffres) |
| `code_nc` | CharField(8) | NULL | Code NC (8 chiffres) |
| `code_taric` | CharField(10) | NULL | Code TARIC (10 chiffres) |
| `chat_historique` | JSONField | DEFAULT [] | Historique du chat |
| `propositions` | JSONField | DEFAULT [] | Propositions TARIC |
| `proposition_selectionnee` | IntegerField | NULL | Index de la proposition choisie |

**Format `chat_historique`:**
```json
[
  {
    "role": "user|assistant|system",
    "content": "Message content",
    "timestamp": "2025-12-18T10:30:00Z"
  }
]
```

**Format `propositions`:**
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

Donnees specifiques a l'etape 2: Generation de Documents (Placeholder).

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | |
| `etape_id` | OneToOneField | UNIQUE | → ExpeditionEtape |
| `dau_genere` | BooleanField | DEFAULT False | DAU genere |
| `d10_genere` | BooleanField | DEFAULT False | D10 genere |
| `d12_genere` | BooleanField | DEFAULT False | D12 genere |

---

### 5. TransmissionData

Donnees specifiques a l'etape 3: Transmission Electronique (Placeholder).

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | |
| `etape_id` | OneToOneField | UNIQUE | → ExpeditionEtape |
| `systeme_cible` | CharField(20) | NULL | DELTA ou BADR |
| `reference_transmission` | CharField(100) | NULL | Reference retournee |
| `date_transmission` | DateTimeField | NULL | Date d'envoi |

---

### 6. PaiementData

Donnees specifiques a l'etape 4: Paiement des Droits (Placeholder).

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | |
| `etape_id` | OneToOneField | UNIQUE | → ExpeditionEtape |
| `montant_droits` | DecimalField | NULL | Montant des droits |
| `montant_tva` | DecimalField | NULL | Montant TVA |
| `reference_paiement` | CharField(100) | NULL | Reference paiement |
| `date_paiement` | DateTimeField | NULL | Date de paiement |

---

### 7. OEAData

Donnees specifiques a l'etape 5: Gestion OEA (Placeholder).

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | |
| `etape_id` | OneToOneField | UNIQUE | → ExpeditionEtape |
| `statut_oea` | CharField(20) | NULL | Statut OEA |
| `numero_certificat` | CharField(100) | NULL | Numero certificat |

---

### 8. ExpeditionDocument

Documents associes a une etape.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `id` | AutoField | PK | |
| `etape_id` | ForeignKey | NOT NULL | → ExpeditionEtape |
| `type` | CharField(30) | NOT NULL | photo/fiche_technique/dau/d10/d12/etc |
| `fichier` | FileField | NOT NULL | Chemin du fichier |
| `nom_original` | CharField(255) | NOT NULL | Nom original |
| `ordre` | IntegerField | DEFAULT 0 | Ordre d'affichage |
| `created_at` | DateTimeField | AUTO | Date de creation |

**Types de documents:**
- `photo` - Photo du produit
- `fiche_technique` - Fiche technique PDF
- `dau` - Document Administratif Unique
- `d10` - Formulaire D10
- `d12` - Formulaire D12
- `ens` - Entry Summary Declaration
- `certificat_origine` - Certificat d'origine
- `autre` - Autre document

---

## Structure des Fichiers Media

```
data/
├── db.sqlite3
└── media_expediciones/
    └── {expedition_id}/
        ├── etape_1_classification/
        │   ├── images/
        │   │   ├── photo_001.jpg
        │   │   └── photo_002.png
        │   └── documents/
        │       └── fiche_technique.pdf
        │
        ├── etape_2_documents/
        │   ├── images/
        │   └── documents/
        │       ├── dau.pdf
        │       └── d10.pdf
        │
        ├── etape_3_transmission/
        │   ├── images/
        │   └── documents/
        │
        ├── etape_4_paiement/
        │   ├── images/
        │   └── documents/
        │
        └── etape_5_oea/
            ├── images/
            └── documents/
```

---

## Diagramme Entite-Relation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │      User        │                                                        │
│  └────────┬─────────┘                                                        │
│           │ 1:N                                                              │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │    Expedition    │                                                        │
│  ├──────────────────┤                                                        │
│  │ reference        │                                                        │
│  │ nom_article      │                                                        │
│  │ direction        │                                                        │
│  │ statut           │                                                        │
│  │ etape_courante   │                                                        │
│  └────────┬─────────┘                                                        │
│           │ 1:5                                                              │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ ExpeditionEtape  │                                                        │
│  ├──────────────────┤                                                        │
│  │ numero (1-5)     │                                                        │
│  │ type_etape       │                                                        │
│  │ statut           │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│     ┌─────┴─────┬──────────┬──────────┬──────────┐                          │
│     │ 1:1       │ 1:1      │ 1:1      │ 1:1      │ 1:1                       │
│     ▼           ▼          ▼          ▼          ▼                          │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                     │
│  │Classif.│ │Docs    │ │Transm. │ │Paiement│ │OEA     │                     │
│  │Data    │ │Data    │ │Data    │ │Data    │ │Data    │                     │
│  ├────────┤ └────────┘ └────────┘ └────────┘ └────────┘                     │
│  │code_sh │                                                                  │
│  │code_nc │                                                                  │
│  │code_   │                                                                  │
│  │taric   │                                                                  │
│  │chat_   │                                                                  │
│  │histor. │                                                                  │
│  │propos. │                                                                  │
│  └────────┘                                                                  │
│           │                                                                  │
│           │ 1:N (via ExpeditionEtape)                                        │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ExpeditionDocument│                                                        │
│  ├──────────────────┤                                                        │
│  │ type             │                                                        │
│  │ fichier          │                                                        │
│  │ nom_original     │                                                        │
│  └──────────────────┘                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Migrations

### Migration depuis l'ancienne structure

L'ancienne structure utilisait:
- `ClassificationChat` - Session de chat
- `ClassificationMessage` - Messages individuels
- `TARICProposal` - Propositions separees

La nouvelle structure consolide tout dans `ClassificationData` avec des champs JSON.

**Script de migration:**
1. Convertir `ClassificationMessage` → `chat_historique` JSON
2. Convertir `TARICProposal` → `propositions` JSON
3. Supprimer les anciennes tables

---

## Index recommandes

```sql
CREATE INDEX idx_expedition_user ON expedition(user_id);
CREATE INDEX idx_expedition_statut ON expedition(statut);
CREATE INDEX idx_etape_expedition ON expeditionetape(expedition_id);
CREATE INDEX idx_etape_numero ON expeditionetape(numero);
CREATE INDEX idx_document_etape ON expeditiondocument(etape_id);
CREATE INDEX idx_document_type ON expeditiondocument(type);
```

---

**Version:** 2.0.0
**Derniere mise a jour:** Decembre 2025
