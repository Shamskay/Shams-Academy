from django.db import migrations


def create_default_grade_boundaries(apps, schema_editor):
    GradeBoundary = apps.get_model('school', 'GradeBoundary')
    if GradeBoundary.objects.exists():
        return
    defaults = [
        ('A', 75, 100, 'Excellent'),
        ('B', 60, 74, 'Good'),
        ('C', 50, 59, 'Average'),
        ('D', 40, 49, 'Below Average'),
        ('F', 0, 39, 'Fail'),
    ]
    for name, min_score, max_score, remark in defaults:
        GradeBoundary.objects.create(
            name=name,
            min_score=min_score,
            max_score=max_score,
            remark=remark,
            is_active=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0010_academicclass_next_class'),
    ]

    operations = [
        migrations.RunPython(create_default_grade_boundaries),
    ]
