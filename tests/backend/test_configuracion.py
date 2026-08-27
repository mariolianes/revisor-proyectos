"""La carpeta de entregas: qué rutas sirven y cuáles no."""

from pathlib import Path

from backend.configuracion import cargar, revisar_carpeta


def test_carpeta_valida_no_da_problema(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()

    assert revisar_carpeta(raiz, carpeta) is None


def test_carpeta_dentro_del_repositorio_se_rechaza(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    carpeta = raiz / "01_ALUMNOS"
    carpeta.mkdir(parents=True)

    problema = revisar_carpeta(raiz, carpeta)

    assert problema is not None
    assert "dentro del repositorio" in problema.motivo


def test_carpeta_que_es_la_propia_raiz_se_rechaza(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()

    problema = revisar_carpeta(raiz, raiz)

    assert problema is not None
    assert "dentro del repositorio" in problema.motivo


def test_carpeta_inexistente_se_rechaza(tmp_path: Path) -> None:
    problema = revisar_carpeta(tmp_path / "repo", tmp_path / "no-existe")

    assert problema is not None
    assert "no existe" in problema.motivo


def test_ruta_que_es_un_fichero_se_rechaza(tmp_path: Path) -> None:
    fichero = tmp_path / "cosa.txt"
    fichero.write_text("x", encoding="utf-8")

    problema = revisar_carpeta(tmp_path / "repo", fichero)

    assert problema is not None
    assert "no es una carpeta" in problema.motivo


def test_el_motivo_dice_que_hacer(tmp_path: Path) -> None:
    """El docente lee esto: ha de saber qué corregir, no solo que falla."""
    raiz = tmp_path / "repo"
    carpeta = raiz / "01_ALUMNOS"
    carpeta.mkdir(parents=True)

    problema = revisar_carpeta(raiz, carpeta)

    assert problema is not None
    assert "REVISOR_CARPETA_ENTREGAS" in problema.motivo


def test_cargar_sin_entorno_deja_todo_vacio(tmp_path: Path) -> None:
    configuracion = cargar(tmp_path, entorno={})

    assert configuracion.carpeta_entregas is None
    assert configuracion.url_supabase is None
    assert configuracion.clave_supabase is None


def test_cargar_lee_la_carpeta_del_entorno(tmp_path: Path) -> None:
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()

    configuracion = cargar(
        tmp_path / "repo",
        entorno={"REVISOR_CARPETA_ENTREGAS": str(carpeta)},
    )

    assert configuracion.carpeta_entregas == carpeta


def test_cargar_descarta_una_carpeta_que_no_sirve(tmp_path: Path) -> None:
    """Una ruta inservible se ignora: no se arrastra media configuración."""
    raiz = tmp_path / "repo"
    dentro = raiz / "01_ALUMNOS"
    dentro.mkdir(parents=True)

    configuracion = cargar(raiz, entorno={"REVISOR_CARPETA_ENTREGAS": str(dentro)})

    assert configuracion.carpeta_entregas is None


def test_cargar_lee_el_fichero_env(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()
    (raiz / ".env").write_text(
        f"# comentario\nREVISOR_CARPETA_ENTREGAS={carpeta}\n"
        "SUPABASE_URL=https://ejemplo.supabase.co\n",
        encoding="utf-8",
    )

    configuracion = cargar(raiz, entorno={})

    assert configuracion.carpeta_entregas == carpeta
    assert configuracion.url_supabase == "https://ejemplo.supabase.co"


def test_el_entorno_manda_sobre_el_fichero(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / ".env").write_text("SUPABASE_URL=del-fichero\n", encoding="utf-8")

    configuracion = cargar(raiz, entorno={"SUPABASE_URL": "del-entorno"})

    assert configuracion.url_supabase == "del-entorno"


def test_version_de_criterios_por_omision(tmp_path: Path) -> None:
    assert cargar(tmp_path, entorno={}).version_criterios == "v2026-2027"
