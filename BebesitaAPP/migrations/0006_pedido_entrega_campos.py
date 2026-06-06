from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("BebesitaAPP", "0005_productoimagen"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="comuna_sector",
            field=models.CharField(default="", max_length=120),
        ),
        migrations.AddField(
            model_name="pedido",
            name="costo_despacho",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="pedido",
            name="tipo_entrega",
            field=models.CharField(
                choices=[("retiro", "Retiro en punto"), ("despacho", "Despacho a domicilio")],
                default="retiro",
                max_length=20,
            ),
        ),
    ]
