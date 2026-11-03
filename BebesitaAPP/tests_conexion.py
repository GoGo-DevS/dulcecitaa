"""Conexion a Neon (03-11-2026): los 500 intermitentes del 02-11.

Ver el comentario en reposteria/settings.py junto a dj_database_url.parse.
"""
from unittest import mock

from django.test import TestCase


class ConexionBaseTests(TestCase):
    """La configuracion de Postgres que arma settings.py con DATABASE_URL.

    Se recarga el modulo de settings con una URL FALSA dentro de un entorno
    parchado: no se conecta a nada y no toca la configuracion con que corren
    las pruebas (SQLite), que Django ya copio al arrancar.
    """

    URL = "postgres://usuario:clave@ejemplo-pooler.neon.tech/basefalsa"

    def _base(self, **entorno):
        import importlib
        import os
        import reposteria.settings as modulo
        try:
            with mock.patch.dict(os.environ, {"DATABASE_URL": self.URL, **entorno}):
                importlib.reload(modulo)
                return dict(modulo.DATABASES["default"])
        finally:
            with mock.patch.dict(os.environ, {"DATABASE_URL": ""}):
                importlib.reload(modulo)

    def test_cada_visita_abre_su_conexion_y_neon_puede_suspender(self):
        base = self._base()
        self.assertIn("postgresql", base["ENGINE"])
        self.assertEqual(base["CONN_MAX_AGE"], 0)
        self.assertEqual(base["OPTIONS"]["sslmode"], "require")

    def test_una_conexion_reutilizada_se_revisa_antes_de_usarla(self):
        base = self._base(DB_CONN_MAX_AGE="60")
        self.assertEqual(base["CONN_MAX_AGE"], 60)
        self.assertTrue(base["CONN_HEALTH_CHECKS"])

    def test_las_pruebas_siguen_en_sqlite(self):
        from django.conf import settings
        from django.db import connection
        self._base()
        self.assertEqual(connection.vendor, "sqlite")
        self.assertIn("sqlite3", settings.DATABASES["default"]["ENGINE"])
