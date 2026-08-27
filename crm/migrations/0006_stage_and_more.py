import uuid
import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify

DEFAULT_STAGES = [
    {'name': 'Lead',        'slug': 'lead',        'color': 'blue',   'order': 0},
    {'name': 'Qualified',   'slug': 'qualified',   'color': 'purple', 'order': 1},
    {'name': 'Proposal',    'slug': 'proposal',    'color': 'amber',  'order': 2},
    {'name': 'Negotiation', 'slug': 'negotiation', 'color': 'orange', 'order': 3},
    {'name': 'Won',         'slug': 'won',         'color': 'green',  'order': 4},
    {'name': 'Lost',        'slug': 'lost',        'color': 'red',    'order': 5},
]


def create_stages_and_migrate_deals(apps, schema_editor):
    Pipeline = apps.get_model('crm', 'Pipeline')
    Stage = apps.get_model('crm', 'Stage')
    CRM = apps.get_model('crm', 'CRM')

    all_stages = []
    pipeline_stage_maps = {}

    for pipeline in Pipeline.objects.all():
        stage_map = {}
        for s in DEFAULT_STAGES:
            sid = uuid.uuid4()
            all_stages.append(Stage(
                id=sid,
                pipeline=pipeline,
                name=s['name'],
                slug=s['slug'],
                color=s['color'],
                order=s['order'],
            ))
            stage_map[s['slug']] = sid
        pipeline_stage_maps[str(pipeline.id)] = stage_map

    Stage.objects.bulk_create(all_stages)

    # Use raw SQL for bulk update to avoid ORM historical model issues
    with schema_editor.connection.cursor() as cursor:
        for pipeline_id, stage_map in pipeline_stage_maps.items():
            for slug, stage_id in stage_map.items():
                cursor.execute(
                    "UPDATE crm_crm SET stage_id = %s WHERE pipeline_id = %s AND stage_old = %s",
                    [str(stage_id), pipeline_id, slug]
                )
        # Default unmapped deals to first stage of their pipeline
        for pipeline_id, stage_map in pipeline_stage_maps.items():
            first_stage_id = list(stage_map.values())[0]
            cursor.execute(
                "UPDATE crm_crm SET stage_id = %s WHERE pipeline_id = %s AND stage_id IS NULL",
                [str(first_stage_id), pipeline_id]
            )


def reverse_migration(apps, schema_editor):
    CRM = apps.get_model('crm', 'CRM')
    Stage = apps.get_model('crm', 'Stage')
    deals = list(CRM.objects.select_related('stage').all())
    for deal in deals:
        deal.stage_old = deal.stage.slug if deal.stage_id else 'lead'
    if deals:
        CRM.objects.bulk_update(deals, ['stage_old'])


def drop_stage_old_physically(apps, schema_editor):
    # Only drop physically on non-sqlite databases to bypass SQLite's table rebuild index bug
    if schema_editor.connection.vendor != 'sqlite':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE crm_crm DROP COLUMN stage_old;")


def add_stage_old_physically(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE crm_crm ADD COLUMN stage_old varchar(100);")


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0003_alter_contact_import_batch'),
        ('crm', '0005_alter_pipeline_name_and_more'),
    ]

    operations = [
        # 1. Create Stage model
        migrations.CreateModel(
            name='Stage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=100)),
                ('order', models.PositiveIntegerField(default=0)),
                ('color', models.CharField(
                    choices=[('blue','Blue'),('purple','Purple'),('amber','Amber'),
                             ('orange','Orange'),('green','Green'),('red','Red'),
                             ('pink','Pink'),('cyan','Cyan')],
                    default='blue', max_length=20
                )),
                ('pipeline', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='stages', to='crm.pipeline'
                )),
            ],
            options={
                'verbose_name': 'Stage',
                'verbose_name_plural': 'Stages',
                'ordering': ['order'],
            },
        ),

        # 2. Rename old stage CharField to stage_old (preserve data)
        migrations.RenameField(
            model_name='crm',
            old_name='stage',
            new_name='stage_old',
        ),

        # 3. Add new stage FK (nullable initially)
        migrations.AddField(
            model_name='crm',
            name='stage',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='deals', to='crm.stage'
            ),
        ),

        # 4. Data migration: create stages per pipeline, map deals
        migrations.RunPython(create_stages_and_migrate_deals, reverse_migration),

        # 5. Drop the old stage_old field (separate state vs database to bypass SQLite index drop bug)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_stage_old_physically, add_stage_old_physically),
            ],
            state_operations=[
                migrations.RemoveField(model_name='crm', name='stage_old'),
            ]
        ),

        # 6. Other field cleanups
        migrations.AlterField(
            model_name='crm',
            name='contact',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='crm_pipelines', to='contacts.contact'
            ),
        ),
        migrations.AlterField(
            model_name='crm',
            name='pipeline',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='deals', to='crm.pipeline'
            ),
        ),
        migrations.AlterField(
            model_name='crm',
            name='value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),

        # 7. Unique together on Stage
        migrations.AlterUniqueTogether(
            name='stage',
            unique_together={('pipeline', 'slug')},
        ),

        # 8. Update index (skip rename - cosmetic only, causes issues with partial state)
        # migrations.RenameIndex(...) removed intentionally
    ]
