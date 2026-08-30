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


def test_cargar_conserva_el_motivo_de_la_carpeta_que_no_sirve(tmp_path: Path) -> None:
    """La carpeta se descarta, pero el motivo no: es lo que lee el docente."""
    raiz = tmp_path / "repo"
    raiz.mkdir()

    configuracion = cargar(
        raiz, entorno={"REVISOR_CARPETA_ENTREGAS": str(tmp_path / "no-existe")}
    )

    assert configuracion.carpeta_entregas is None
    assert configuracion.problema_carpeta is not None
    assert "no existe" in configuracion.problema_carpeta


def test_sin_carpeta_indicada_no_hay_problema_que_contar(tmp_path: Path) -> None:
    """No indicar ninguna no es lo mismo que indicar una que no sirve."""
    assert cargar(tmp_path, entorno={}).problema_carpeta is None


def test_una_carpeta_que_sirve_no_deja_problema(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    carpeta = tmp_path / "entregas"
    carpeta.mkdir()

    configuracion = cargar(raiz, entorno={"REVISOR_CARPETA_ENTREGAS": str(carpeta)})

    assert configuracion.problema_carpeta is None


def test_cargar_lee_la_clave_de_servicio_del_entorno(tmp_path: Path) -> None:
    """SUPABASE_SERVICE_KEY es lo que decide si se guarda de verdad.

    Sin ella `crear_almacen` se queda en memoria, y lo que el docente
    registre se pierde al cerrar. Que se lea no lo fijaba ningún test:
    ignorándola, los 387 de la rama seguían pasando.
    """
    configuracion = cargar(tmp_path, entorno={"SUPABASE_SERVICE_KEY": "la-clave"})

    assert configuracion.clave_supabase == "la-clave"


def test_cargar_lee_la_clave_de_servicio_del_fichero_env(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / ".env").write_text(
        "SUPABASE_SERVICE_KEY=la-clave-del-fichero\n", encoding="utf-8"
    )

    assert cargar(raiz, entorno={}).clave_supabase == "la-clave-del-fichero"


def test_cargar_lee_la_version_de_criterios_del_entorno(tmp_path: Path) -> None:
    """No es decorativa: elige el fichero con el que se corrige un trabajo."""
    configuracion = cargar(
        tmp_path, entorno={"REVISOR_VERSION_CRITERIOS": "v2027-2028"}
    )

    assert configuracion.version_criterios == "v2027-2028"


def test_cargar_lee_la_version_de_criterios_del_fichero_env(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / ".env").write_text(
        "REVISOR_VERSION_CRITERIOS=v2027-2028\n", encoding="utf-8"
    )

    assert cargar(raiz, entorno={}).version_criterios == "v2027-2028"


def test_una_version_de_criterios_vacia_no_deja_al_sistema_sin_version(
    tmp_path: Path,
) -> None:
    """Una línea `REVISOR_VERSION_CRITERIOS=` no debe dejarla en blanco."""
    configuracion = cargar(tmp_path, entorno={"REVISOR_VERSION_CRITERIOS": ""})

    assert configuracion.version_criterios == "v2026-2027"


def test_cargar_sin_entorno_deja_el_analisis_sin_configurar(tmp_path: Path) -> None:
    """Sin clave ni modelo, `crear_proveedor` debe caer en el simulado."""
    configuracion = cargar(tmp_path, entorno={})

    assert configuracion.clave_openai is None
    assert configuracion.modelo_analisis is None


def test_cargar_lee_la_clave_de_openai_del_entorno(tmp_path: Path) -> None:
    configuracion = cargar(tmp_path, entorno={"OPENAI_API_KEY": "sk-de-prueba"})

    assert configuracion.clave_openai == "sk-de-prueba"


def test_cargar_lee_el_modelo_de_analisis_del_entorno(tmp_path: Path) -> None:
    configuracion = cargar(
        tmp_path, entorno={"REVISOR_MODELO_ANALISIS": "el-modelo-elegido"}
    )

    assert configuracion.modelo_analisis == "el-modelo-elegido"


def test_cargar_lee_la_clave_de_openai_del_fichero_env(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / ".env").write_text("OPENAI_API_KEY=sk-del-fichero\n", encoding="utf-8")

    assert cargar(raiz, entorno={}).clave_openai == "sk-del-fichero"


def test_cargar_lee_el_modelo_de_analisis_del_fichero_env(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / ".env").write_text(
        "REVISOR_MODELO_ANALISIS=modelo-del-fichero\n", encoding="utf-8"
    )

    assert cargar(raiz, entorno={}).modelo_analisis == "modelo-del-fichero"


def test_el_entorno_manda_sobre_el_fichero_para_la_clave_de_openai(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / ".env").write_text("OPENAI_API_KEY=sk-del-fichero\n", encoding="utf-8")

    configuracion = cargar(raiz, entorno={"OPENAI_API_KEY": "sk-del-entorno"})

    assert configuracion.clave_openai == "sk-del-entorno"


def test_un_modelo_de_analisis_vacio_no_cuenta_como_configurado(
    tmp_path: Path,
) -> None:
    """Una línea `REVISOR_MODELO_ANALISIS=` sin valor no debe colar un
    modelo vacío que luego rompa `ProveedorOpenAI`."""
    configuracion = cargar(tmp_path, entorno={"REVISOR_MODELO_ANALISIS": ""})

    assert configuracion.modelo_analisis is None


def test_sin_datos_locales_indicados_no_hay_carpeta_ni_problema(tmp_path: Path) -> None:
    configuracion = cargar(tmp_path)

    assert configuracion.datos_locales is None
    assert configuracion.problema_datos_locales is None


def test_cargar_lee_la_carpeta_de_datos_locales_del_entorno(tmp_path: Path) -> None:
    carpeta = tmp_path / "datos_locales"
    carpeta.mkdir()

    configuracion = cargar(
        tmp_path / "repo", entorno={"REVISOR_DATOS_LOCALES": str(carpeta)},
    )

    assert configuracion.datos_locales == carpeta


def test_datos_locales_dentro_del_repositorio_se_rechaza(tmp_path: Path) -> None:
    """Misma exigencia que la carpeta de entregas, y por el mismo motivo: lo
    que vive ahí no se versiona nunca."""
    raiz = tmp_path / "repo"
    dentro = raiz / "listado_local"
    dentro.mkdir(parents=True)

    configuracion = cargar(raiz, entorno={"REVISOR_DATOS_LOCALES": str(dentro)})

    assert configuracion.datos_locales is None
    assert "dentro del repositorio" in configuracion.problema_datos_locales
