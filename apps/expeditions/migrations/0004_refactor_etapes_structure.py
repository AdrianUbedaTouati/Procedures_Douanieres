# Generated manually for refactoring expedition structure
# Adds type_etape to ExpeditionEtape and creates new data tables

import django.db.models.deletion
from django.db import migrations, models
import apps.expeditions.models


def set_type_etape_from_numero(apps, schema_editor):
    """Migrate type_etape based on numero field."""
    ExpeditionEtape = apps.get_model('expeditions', 'ExpeditionEtape')
    type_mapping = {
        1: 'classification',
        2: 'documents',
        3: 'transmission',
        4: 'paiement',
        5: 'oea',
    }
    for etape in ExpeditionEtape.objects.all():
        etape.type_etape = type_mapping.get(etape.numero, 'classification')
        etape.save()


def set_etape_for_documents(apps, schema_editor):
    """Ensure all documents have an etape assigned."""
    ExpeditionDocument = apps.get_model('expeditions', 'ExpeditionDocument')
    ExpeditionEtape = apps.get_model('expeditions', 'ExpeditionEtape')

    for doc in ExpeditionDocument.objects.filter(etape__isnull=True):
        # Get the first etape of the expedition (classification)
        etape = ExpeditionEtape.objects.filter(
            expedition_id=doc.expedition_id,
            numero=1
        ).first()
        if etape:
            doc.etape = etape
            doc.save()


def create_classification_data(apps, schema_editor):
    """Create ClassificationData for existing etapes."""
    ExpeditionEtape = apps.get_model('expeditions', 'ExpeditionEtape')
    ClassificationData = apps.get_model('expeditions', 'ClassificationData')

    for etape in ExpeditionEtape.objects.filter(numero=1):
        if not ClassificationData.objects.filter(etape=etape).exists():
            # Migrate data from donnees JSONField if available
            donnees = etape.donnees or {}
            ClassificationData.objects.create(
                etape=etape,
                code_sh=donnees.get('code_sh', ''),
                code_nc=donnees.get('code_nc', ''),
                code_taric=donnees.get('code_taric', ''),
                chat_historique=[],
                propositions=[],
                proposition_selectionnee=None
            )


def create_placeholder_data(apps, schema_editor):
    """Create placeholder data tables for etapes 2-5."""
    ExpeditionEtape = apps.get_model('expeditions', 'ExpeditionEtape')
    DocumentsData = apps.get_model('expeditions', 'DocumentsData')
    TransmissionData = apps.get_model('expeditions', 'TransmissionData')
    PaiementData = apps.get_model('expeditions', 'PaiementData')
    OEAData = apps.get_model('expeditions', 'OEAData')

    for etape in ExpeditionEtape.objects.filter(numero=2):
        if not DocumentsData.objects.filter(etape=etape).exists():
            DocumentsData.objects.create(etape=etape)

    for etape in ExpeditionEtape.objects.filter(numero=3):
        if not TransmissionData.objects.filter(etape=etape).exists():
            TransmissionData.objects.create(etape=etape)

    for etape in ExpeditionEtape.objects.filter(numero=4):
        if not PaiementData.objects.filter(etape=etape).exists():
            PaiementData.objects.create(etape=etape)

    for etape in ExpeditionEtape.objects.filter(numero=5):
        if not OEAData.objects.filter(etape=etape).exists():
            OEAData.objects.create(etape=etape)


class Migration(migrations.Migration):

    dependencies = [
        ('expeditions', '0003_add_classification_chat_models'),
    ]

    operations = [
        # Step 1: Add type_etape field with default
        migrations.AddField(
            model_name='expeditionetape',
            name='type_etape',
            field=models.CharField(
                choices=[
                    ('classification', 'Classification'),
                    ('documents', 'Documents'),
                    ('transmission', 'Transmission'),
                    ('paiement', 'Paiement'),
                    ('oea', 'OEA'),
                ],
                default='classification',
                max_length=20,
                verbose_name="Type d'etape"
            ),
        ),

        # Step 2: Migrate type_etape values from numero
        migrations.RunPython(set_type_etape_from_numero, migrations.RunPython.noop),

        # Step 3: Create ClassificationData table
        migrations.CreateModel(
            name='ClassificationData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_sh', models.CharField(blank=True, max_length=6, null=True, verbose_name='Code SH (6 chiffres)')),
                ('code_nc', models.CharField(blank=True, max_length=8, null=True, verbose_name='Code NC (8 chiffres)')),
                ('code_taric', models.CharField(blank=True, max_length=10, null=True, verbose_name='Code TARIC (10 chiffres)')),
                ('chat_historique', models.JSONField(blank=True, default=list, help_text='Liste des messages [{role, content, timestamp}, ...]', verbose_name='Historique du chat')),
                ('propositions', models.JSONField(blank=True, default=list, help_text='Liste des propositions [{code_taric, probability, description, justification}, ...]', verbose_name='Propositions TARIC')),
                ('proposition_selectionnee', models.IntegerField(blank=True, help_text='Index de la proposition choisie dans la liste', null=True, verbose_name='Proposition selectionnee')),
                ('etape', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='classification_data', to='expeditions.expeditionetape', verbose_name='Etape')),
            ],
            options={
                'verbose_name': 'Donnees Classification',
                'verbose_name_plural': 'Donnees Classification',
            },
        ),

        # Step 4: Create DocumentsData table
        migrations.CreateModel(
            name='DocumentsData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dau_genere', models.BooleanField(default=False, verbose_name='DAU genere')),
                ('d10_genere', models.BooleanField(default=False, verbose_name='D10 genere')),
                ('d12_genere', models.BooleanField(default=False, verbose_name='D12 genere')),
                ('etape', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='documents_data', to='expeditions.expeditionetape', verbose_name='Etape')),
            ],
            options={
                'verbose_name': 'Donnees Documents',
                'verbose_name_plural': 'Donnees Documents',
            },
        ),

        # Step 5: Create TransmissionData table
        migrations.CreateModel(
            name='TransmissionData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('systeme_cible', models.CharField(blank=True, help_text='DELTA ou BADR', max_length=20, null=True, verbose_name='Systeme cible')),
                ('reference_transmission', models.CharField(blank=True, max_length=100, null=True, verbose_name='Reference transmission')),
                ('date_transmission', models.DateTimeField(blank=True, null=True, verbose_name='Date de transmission')),
                ('etape', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='transmission_data', to='expeditions.expeditionetape', verbose_name='Etape')),
            ],
            options={
                'verbose_name': 'Donnees Transmission',
                'verbose_name_plural': 'Donnees Transmission',
            },
        ),

        # Step 6: Create PaiementData table
        migrations.CreateModel(
            name='PaiementData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('montant_droits', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Montant des droits')),
                ('montant_tva', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Montant TVA')),
                ('reference_paiement', models.CharField(blank=True, max_length=100, null=True, verbose_name='Reference paiement')),
                ('date_paiement', models.DateTimeField(blank=True, null=True, verbose_name='Date de paiement')),
                ('etape', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='paiement_data', to='expeditions.expeditionetape', verbose_name='Etape')),
            ],
            options={
                'verbose_name': 'Donnees Paiement',
                'verbose_name_plural': 'Donnees Paiement',
            },
        ),

        # Step 7: Create OEAData table
        migrations.CreateModel(
            name='OEAData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('statut_oea', models.CharField(blank=True, max_length=20, null=True, verbose_name='Statut OEA')),
                ('numero_certificat', models.CharField(blank=True, max_length=100, null=True, verbose_name='Numero certificat')),
                ('etape', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='oea_data', to='expeditions.expeditionetape', verbose_name='Etape')),
            ],
            options={
                'verbose_name': 'Donnees OEA',
                'verbose_name_plural': 'Donnees OEA',
            },
        ),

        # Step 8: Set etape for existing documents
        migrations.RunPython(set_etape_for_documents, migrations.RunPython.noop),

        # Step 9: Create data entries for existing etapes
        migrations.RunPython(create_classification_data, migrations.RunPython.noop),
        migrations.RunPython(create_placeholder_data, migrations.RunPython.noop),

        # Step 10: Remove expedition FK from ExpeditionDocument (now uses etape only)
        migrations.RemoveField(
            model_name='expeditiondocument',
            name='expedition',
        ),

        # Step 11: Make etape non-nullable
        migrations.AlterField(
            model_name='expeditiondocument',
            name='etape',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='documents',
                to='expeditions.expeditionetape',
                verbose_name='Etape'
            ),
        ),

        # Step 12: Update ExpeditionDocument fichier field to use dynamic upload_to
        migrations.AlterField(
            model_name='expeditiondocument',
            name='fichier',
            field=models.FileField(
                upload_to=apps.expeditions.models.document_upload_path,
                verbose_name='Fichier'
            ),
        ),

        # Step 13: Add ordre field if it doesn't exist
        # (Already exists from migration 0002)

        # Step 14: Update ordering for ExpeditionDocument
        migrations.AlterModelOptions(
            name='expeditiondocument',
            options={
                'ordering': ['type', 'ordre', '-created_at'],
                'verbose_name': "Document d'expedition",
                'verbose_name_plural': "Documents d'expedition"
            },
        ),

        # Step 15: Remove old chat models
        migrations.DeleteModel(
            name='TARICProposal',
        ),
        migrations.DeleteModel(
            name='ClassificationMessage',
        ),
        migrations.DeleteModel(
            name='ClassificationChat',
        ),

        # Step 16: Remove donnees field from ExpeditionEtape
        migrations.RemoveField(
            model_name='expeditionetape',
            name='donnees',
        ),
    ]
