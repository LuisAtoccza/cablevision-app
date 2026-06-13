#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE GESTION OPERATIVA Y SST - CABLEVISION PERU V2
Planta Externa - Supervisor de Planta Externa
Desarrollado: Junio 2026
Tecnologias: Flask + SQLite + Jinja2 + Bootstrap 5
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import os
import hashlib
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'Cablevision_Peru_2026_V2_Secret_Key_Planta_Externa_SST'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'xlsx', 'doc', 'docx', 'mp4', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

DATABASE = 'database/cablevision_v2.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Tabla: Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('supervisor', 'asistente', 'tecnico', 'contratista')),
            cuadrilla_id INTEGER,
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cuadrilla_id) REFERENCES equipos(id)
        )
    """)

    # Tabla: Equipos/Cuadrillas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('cuadrilla', 'contratista', 'administrativo')),
            nombre TEXT NOT NULL,
            miembro1 TEXT,
            miembro2 TEXT,
            estado TEXT DEFAULT 'disponible' CHECK(estado IN ('disponible', 'ocupado', 'activo', 'inactivo')),
            proyecto_actual_id INTEGER,
            disponible_desde DATE,
            rendimiento INTEGER DEFAULT 0,
            observaciones TEXT,
            FOREIGN KEY (proyecto_actual_id) REFERENCES proyectos(id)
        )
    """)

    # Tabla: Tipos de Proyectos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tipos_proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefijo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    # Tabla: Estados de Proyecto
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estados_proyecto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estado TEXT UNIQUE NOT NULL,
            color_semaforo TEXT,
            descripcion TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    # Tabla: Proyectos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            tipo_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            anio INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            ubicacion TEXT,
            zona_distrito TEXT,
            estado_id INTEGER NOT NULL,
            fecha_inicio DATE,
            fecha_fin_estimada DATE,
            fecha_fin_real DATE,
            responsable_id INTEGER,
            contratista_id INTEGER,
            avance INTEGER DEFAULT 0,
            costo_estimado REAL,
            certificacion_estado TEXT DEFAULT 'PENDIENTE',
            plano_semaforo TEXT DEFAULT 'PENDIENTE',
            observaciones TEXT,
            creado_por INTEGER,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tipo_id) REFERENCES tipos_proyectos(id),
            FOREIGN KEY (estado_id) REFERENCES estados_proyecto(id),
            FOREIGN KEY (responsable_id) REFERENCES usuarios(id),
            FOREIGN KEY (contratista_id) REFERENCES equipos(id),
            FOREIGN KEY (creado_por) REFERENCES usuarios(id)
        )
    """)

    # Tabla: Asistencia
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            usuario_id INTEGER NOT NULL,
            hora_entrada TIME,
            hora_salida TIME,
            estado TEXT CHECK(estado IN ('PRESENTE', 'TARDANZA', 'AUSENTE', 'PERMISO', 'FERIADO')),
            observaciones TEXT,
            registrado_por INTEGER,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (registrado_por) REFERENCES usuarios(id)
        )
    """)

    # Tabla: ATS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id INTEGER,
            fecha DATE NOT NULL,
            usuario_id INTEGER NOT NULL,
            actividad TEXT NOT NULL,
            riesgos_identificados TEXT,
            medidas_preventivas TEXT,
            epp_requeridos TEXT,
            estado TEXT DEFAULT 'PENDIENTE' CHECK(estado IN ('PENDIENTE', 'APROBADO', 'RECHAZADO', 'VENCIDO')),
            archivo_url TEXT,
            aprobado_por INTEGER,
            fecha_aprobacion DATE,
            observaciones TEXT,
            FOREIGN KEY (proyecto_id) REFERENCES proyectos(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (aprobado_por) REFERENCES usuarios(id)
        )
    """)

    # Tabla: Fotos EPPs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fotos_epps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            usuario_id INTEGER NOT NULL,
            proyecto_id INTEGER,
            tipo_epp TEXT CHECK(tipo_epp IN ('CASCO', 'CHALECO', 'GUANTES', 'LENTES', 'BOTAS', 'ARNES', 'TAPAOIDOS', 'OTROS')),
            foto_url TEXT NOT NULL,
            estado_epp TEXT CHECK(estado_epp IN ('CORRECTO', 'DANADO', 'INCOMPLETO')),
            observaciones TEXT,
            registrado_por INTEGER,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (proyecto_id) REFERENCES proyectos(id),
            FOREIGN KEY (registrado_por) REFERENCES usuarios(id)
        )
    """)

    # Tabla: Charlas SST
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS charlas_sst (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            tema TEXT NOT NULL,
            instructor_id INTEGER NOT NULL,
            duracion_minutos INTEGER DEFAULT 5,
            asistentes TEXT,
            cantidad_asistentes INTEGER,
            evidencia_foto_url TEXT,
            resumen TEXT,
            estado TEXT DEFAULT 'REALIZADA',
            FOREIGN KEY (instructor_id) REFERENCES usuarios(id)
        )
    """)

    # Tabla: Liquidacion Kari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS liquidacion_kari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyecto_id INTEGER NOT NULL,
            fecha_liquidacion DATE,
            liquidado_por INTEGER NOT NULL,
            estado_liquidacion TEXT DEFAULT 'PENDIENTE' CHECK(estado_liquidacion IN ('PENDIENTE', 'EN REVISION', 'APROBADO', 'RECHAZADO', 'OBSERVADO')),
            observaciones_liquidacion TEXT,
            aprobado_por INTEGER,
            fecha_aprobacion DATE,
            FOREIGN KEY (proyecto_id) REFERENCES proyectos(id),
            FOREIGN KEY (liquidado_por) REFERENCES usuarios(id),
            FOREIGN KEY (aprobado_por) REFERENCES usuarios(id)
        )
    """)

    # Tabla: Configuracion
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parametro TEXT UNIQUE NOT NULL,
            valor TEXT NOT NULL,
            descripcion TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Base de datos V2 inicializada")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debe iniciar sesion', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def supervisor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rol' not in session or session['rol'] != 'supervisor':
            flash('Acceso restringido', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def generar_codigo_proyecto(tipo_prefijo, anio):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(numero) FROM proyectos p JOIN tipos_proyectos t ON p.tipo_id = t.id WHERE t.prefijo = ? AND p.anio = ?', (tipo_prefijo, anio))
    result = cursor.fetchone()
    conn.close()
    ultimo = result[0] if result[0] else 0
    nuevo = ultimo + 1
    return f"{tipo_prefijo}-{nuevo:03d}-{anio}", nuevo

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hash_password(password)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, nombre, rol, cuadrilla_id FROM usuarios WHERE username = ? AND password_hash = ? AND activo = 1', (username, password_hash))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nombre'] = user['nombre']
            session['rol'] = user['rol']
            session['cuadrilla_id'] = user['cuadrilla_id']
            flash(f'Bienvenido {user["nombre"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contrasena incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesion cerrada', 'info')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM proyectos')
    total_proyectos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM proyectos WHERE estado_id IN (SELECT id FROM estados_proyecto WHERE estado IN ('EN PROCESO', 'ASIGNADO'))")
    activos = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM proyectos WHERE estado_id IN (SELECT id FROM estados_proyecto WHERE estado = 'COMPLETADO')")
    completados = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM asistencia WHERE fecha = ? AND estado = 'PRESENTE'", (datetime.now().strftime('%Y-%m-%d'),))
    asistencia_hoy = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ats WHERE estado = 'PENDIENTE'")
    ats_pendientes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM charlas_sst WHERE fecha >= ?", ((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),))
    charlas_mes = cursor.fetchone()[0]
    cursor.execute('SELECT t.prefijo, t.nombre, COUNT(*) as cantidad FROM proyectos p JOIN tipos_proyectos t ON p.tipo_id = t.id GROUP BY t.prefijo')
    proyectos_tipo = cursor.fetchall()
    cursor.execute('SELECT * FROM equipos ORDER BY tipo, nombre')
    equipos = cursor.fetchall()
    fecha_limite = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute('SELECT p.*, t.prefijo, t.nombre as tipo_nombre, e.estado as estado_nombre, e.color_semaforo FROM proyectos p JOIN tipos_proyectos t ON p.tipo_id = t.id JOIN estados_proyecto e ON p.estado_id = e.id WHERE p.fecha_fin_estimada <= ? AND e.estado IN ("EN PROCESO", "ASIGNADO") ORDER BY p.fecha_fin_estimada ASC', (fecha_limite,))
    urgentes = cursor.fetchall()
    cursor.execute('SELECT a.*, u.nombre FROM asistencia a JOIN usuarios u ON a.usuario_id = u.id WHERE a.fecha = ? ORDER BY u.nombre', (datetime.now().strftime('%Y-%m-%d'),))
    asistencia_hoy_list = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', total_proyectos=total_proyectos, activos=activos, completados=completados, asistencia_hoy=asistencia_hoy, ats_pendientes=ats_pendientes, charlas_mes=charlas_mes, proyectos_tipo=proyectos_tipo, equipos=equipos, urgentes=urgentes, asistencia_hoy_list=asistencia_hoy_list, now=datetime.now())

@app.route('/proyectos')
@login_required
def proyectos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT p.*, t.prefijo, t.nombre as tipo_nombre, e.estado as estado_nombre, e.color_semaforo, u.nombre as responsable_nombre, eq.nombre as contratista_nombre FROM proyectos p JOIN tipos_proyectos t ON p.tipo_id = t.id JOIN estados_proyecto e ON p.estado_id = e.id LEFT JOIN usuarios u ON p.responsable_id = u.id LEFT JOIN equipos eq ON p.contratista_id = eq.id ORDER BY p.fecha_creacion DESC')
    proyectos_list = cursor.fetchall()
    conn.close()
    return render_template('proyectos.html', proyectos=proyectos_list)

@app.route('/proyectos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_proyecto():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        tipo_id = request.form['tipo_id']
        anio = int(request.form['anio'])
        nombre = request.form['nombre']
        ubicacion = request.form.get('ubicacion')
        zona = request.form.get('zona')
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin_estimada']
        costo = request.form.get('costo_estimado')
        observaciones = request.form.get('observaciones')
        cursor.execute('SELECT prefijo FROM tipos_proyectos WHERE id = ?', (tipo_id,))
        prefijo = cursor.fetchone()['prefijo']
        codigo, numero = generar_codigo_proyecto(prefijo, anio)
        cursor.execute('SELECT id FROM estados_proyecto WHERE estado = "PENDIENTE"')
        estado_id = cursor.fetchone()['id']
        cursor.execute('INSERT INTO proyectos (codigo, tipo_id, numero, anio, nombre, ubicacion, zona_distrito, estado_id, fecha_inicio, fecha_fin_estimada, costo_estimado, observaciones, creado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (codigo, tipo_id, numero, anio, nombre, ubicacion, zona, estado_id, fecha_inicio, fecha_fin, costo, observaciones, session['user_id']))
        conn.commit()
        conn.close()
        flash(f'Proyecto {codigo} creado', 'success')
        return redirect(url_for('proyectos'))
    cursor.execute('SELECT * FROM tipos_proyectos WHERE activo = 1 ORDER BY prefijo')
    tipos = cursor.fetchall()
    cursor.execute('SELECT * FROM estados_proyecto WHERE activo = 1 ORDER BY id')
    estados = cursor.fetchall()
    cursor.execute('SELECT id, nombre FROM usuarios WHERE rol IN ("tecnico", "contratista") AND activo = 1')
    responsables = cursor.fetchall()
    cursor.execute('SELECT id, nombre FROM equipos WHERE tipo = "contratista" AND activo = 1')
    contratistas = cursor.fetchall()
    conn.close()
    return render_template('proyecto_form.html', tipos=tipos, estados=estados, responsables=responsables, contratistas=contratistas, proyecto=None)

@app.route('/proyectos/<int:id>')
@login_required
def ver_proyecto(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT p.*, t.prefijo, t.nombre as tipo_nombre, e.estado as estado_nombre, e.color_semaforo, u.nombre as responsable_nombre, eq.nombre as contratista_nombre FROM proyectos p JOIN tipos_proyectos t ON p.tipo_id = t.id JOIN estados_proyecto e ON p.estado_id = e.id LEFT JOIN usuarios u ON p.responsable_id = u.id LEFT JOIN equipos eq ON p.contratista_id = eq.id WHERE p.id = ?', (id,))
    proyecto = cursor.fetchone()
    if not proyecto:
        flash('Proyecto no encontrado', 'danger')
        return redirect(url_for('proyectos'))
    cursor.execute('SELECT * FROM ats WHERE proyecto_id = ?', (id,))
    ats_list = cursor.fetchall()
    cursor.execute('SELECT * FROM fotos_epps WHERE proyecto_id = ?', (id,))
    epps = cursor.fetchall()
    conn.close()
    return render_template('proyecto_detalle.html', proyecto=proyecto, ats_list=ats_list, epps=epps)

# ASISTENCIA
@app.route('/asistencia')
@login_required
def asistencia():
    conn = get_db()
    cursor = conn.cursor()
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    cursor.execute('SELECT a.*, u.nombre, u.rol FROM asistencia a JOIN usuarios u ON a.usuario_id = u.id WHERE a.fecha = ? ORDER BY u.nombre', (fecha,))
    asistencia_list = cursor.fetchall()
    cursor.execute('SELECT id, nombre, rol FROM usuarios WHERE activo = 1 ORDER BY nombre')
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('sst/asistencia.html', asistencia=asistencia_list, usuarios=usuarios, fecha=fecha)

@app.route('/asistencia/registrar', methods=['POST'])
@login_required
def registrar_asistencia():
    fecha = request.form['fecha']
    usuario_id = request.form['usuario_id']
    hora_entrada = request.form.get('hora_entrada')
    hora_salida = request.form.get('hora_salida')
    estado = request.form['estado']
    observaciones = request.form.get('observaciones')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO asistencia (fecha, usuario_id, hora_entrada, hora_salida, estado, observaciones, registrado_por) VALUES (?, ?, ?, ?, ?, ?, ?)', (fecha, usuario_id, hora_entrada, hora_salida, estado, observaciones, session['user_id']))
    conn.commit()
    conn.close()
    flash('Asistencia registrada', 'success')
    return redirect(url_for('asistencia', fecha=fecha))

# ATS
@app.route('/ats')
@login_required
def ats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT a.*, u.nombre as usuario_nombre, p.codigo as proyecto_codigo FROM ats a JOIN usuarios u ON a.usuario_id = u.id LEFT JOIN proyectos p ON a.proyecto_id = p.id ORDER BY a.fecha DESC')
    ats_list = cursor.fetchall()
    conn.close()
    return render_template('sst/ats.html', ats_list=ats_list)

@app.route('/ats/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_ats():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        proyecto_id = request.form.get('proyecto_id') or None
        fecha = request.form['fecha']
        usuario_id = request.form['usuario_id']
        actividad = request.form['actividad']
        riesgos = request.form.get('riesgos_identificados')
        medidas = request.form.get('medidas_preventivas')
        epp = request.form.get('epp_requeridos')
        observaciones = request.form.get('observaciones')
        archivo_url = None
        if 'archivo' in request.files:
            file = request.files['archivo']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"ATS_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'ats', filename))
                archivo_url = f"uploads/ats/{filename}"
        cursor.execute('INSERT INTO ats (proyecto_id, fecha, usuario_id, actividad, riesgos_identificados, medidas_preventivas, epp_requeridos, archivo_url, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (proyecto_id, fecha, usuario_id, actividad, riesgos, medidas, epp, archivo_url, observaciones))
        conn.commit()
        conn.close()
        flash('ATS registrado', 'success')
        return redirect(url_for('ats'))
    cursor.execute('SELECT id, codigo, nombre FROM proyectos WHERE estado_id IN (SELECT id FROM estados_proyecto WHERE estado IN ("EN PROCESO", "ASIGNADO"))')
    proyectos = cursor.fetchall()
    cursor.execute('SELECT id, nombre FROM usuarios WHERE activo = 1 ORDER BY nombre')
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('sst/ats_form.html', proyectos=proyectos, usuarios=usuarios)

@app.route('/ats/<int:id>/aprobar', methods=['POST'])
@login_required
def aprobar_ats(id):
    estado = request.form['estado']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE ats SET estado = ?, aprobado_por = ?, fecha_aprobacion = ? WHERE id = ?', (estado, session['user_id'], datetime.now().strftime('%Y-%m-%d'), id))
    conn.commit()
    conn.close()
    flash(f'ATS {estado}', 'success')
    return redirect(url_for('ats'))

# EPPs
@app.route('/epps')
@login_required
def epps():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT e.*, u.nombre as usuario_nombre, p.codigo as proyecto_codigo FROM fotos_epps e JOIN usuarios u ON e.usuario_id = u.id LEFT JOIN proyectos p ON e.proyecto_id = p.id ORDER BY e.fecha DESC')
    epps_list = cursor.fetchall()
    conn.close()
    return render_template('sst/epps.html', epps=epps_list)

@app.route('/epps/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_epp():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        fecha = request.form['fecha']
        usuario_id = request.form['usuario_id']
        proyecto_id = request.form.get('proyecto_id') or None
        tipo_epp = request.form['tipo_epp']
        estado_epp = request.form['estado_epp']
        observaciones = request.form.get('observaciones')
        foto_url = None
        if 'foto' in request.files:
            file = request.files['foto']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"EPP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'epps', filename))
                foto_url = f"uploads/epps/{filename}"
        cursor.execute('INSERT INTO fotos_epps (fecha, usuario_id, proyecto_id, tipo_epp, foto_url, estado_epp, observaciones, registrado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (fecha, usuario_id, proyecto_id, tipo_epp, foto_url, estado_epp, observaciones, session['user_id']))
        conn.commit()
        conn.close()
        flash('Foto EPP registrada', 'success')
        return redirect(url_for('epps'))
    cursor.execute('SELECT id, nombre FROM usuarios WHERE activo = 1 ORDER BY nombre')
    usuarios = cursor.fetchall()
    cursor.execute('SELECT id, codigo FROM proyectos WHERE estado_id IN (SELECT id FROM estados_proyecto WHERE estado IN ("EN PROCESO", "ASIGNADO"))')
    proyectos = cursor.fetchall()
    conn.close()
    return render_template('sst/epp_form.html', usuarios=usuarios, proyectos=proyectos)

# CHARLAS SST
@app.route('/charlas')
@login_required
def charlas():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT c.*, u.nombre as instructor_nombre FROM charlas_sst c JOIN usuarios u ON c.instructor_id = u.id ORDER BY c.fecha DESC')
    charlas_list = cursor.fetchall()
    conn.close()
    return render_template('sst/charlas.html', charlas=charlas_list)

@app.route('/charlas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_charla():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        fecha = request.form['fecha']
        tema = request.form['tema']
        instructor_id = request.form['instructor_id']
        duracion = request.form.get('duracion', 5)
        asistentes = request.form.get('asistentes')
        cantidad = request.form.get('cantidad_asistentes')
        resumen = request.form.get('resumen')
        evidencia_url = None
        if 'evidencia' in request.files:
            file = request.files['evidencia']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"CHARLA_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'charlas', filename))
                evidencia_url = f"uploads/charlas/{filename}"
        cursor.execute('INSERT INTO charlas_sst (fecha, tema, instructor_id, duracion_minutos, asistentes, cantidad_asistentes, evidencia_foto_url, resumen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (fecha, tema, instructor_id, duracion, asistentes, cantidad, evidencia_url, resumen))
        conn.commit()
        conn.close()
        flash('Charla SST registrada', 'success')
        return redirect(url_for('charlas'))
    cursor.execute('SELECT id, nombre FROM usuarios WHERE activo = 1 ORDER BY nombre')
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('sst/charla_form.html', usuarios=usuarios)

# LIQUIDACION KARI
@app.route('/liquidacion-kari')
@login_required
def liquidacion_kari():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT lk.*, p.codigo, p.nombre as proyecto_nombre, u.nombre as liquidado_nombre, a.nombre as aprobado_nombre FROM liquidacion_kari lk JOIN proyectos p ON lk.proyecto_id = p.id JOIN usuarios u ON lk.liquidado_por = u.id LEFT JOIN usuarios a ON lk.aprobado_por = a.id ORDER BY lk.fecha_liquidacion DESC')
    liquidaciones = cursor.fetchall()
    conn.close()
    return render_template('sst/liquidacion_kari.html', liquidaciones=liquidaciones)

@app.route('/liquidacion-kari/nueva', methods=['GET', 'POST'])
@login_required
def nueva_liquidacion_kari():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        proyecto_id = request.form['proyecto_id']
        fecha = request.form['fecha_liquidacion']
        observaciones = request.form.get('observaciones')
        cursor.execute('SELECT id FROM usuarios WHERE nombre LIKE "%Kari%" OR nombre LIKE "%kari%" LIMIT 1')
        kari = cursor.fetchone()
        liquidado_por = kari['id'] if kari else session['user_id']
        cursor.execute('INSERT INTO liquidacion_kari (proyecto_id, fecha_liquidacion, liquidado_por, observaciones_liquidacion) VALUES (?, ?, ?, ?)', (proyecto_id, fecha, liquidado_por, observaciones))
        conn.commit()
        conn.close()
        flash('Liquidacion registrada', 'success')
        return redirect(url_for('liquidacion_kari'))
    cursor.execute('SELECT id, codigo, nombre FROM proyectos WHERE estado_id IN (SELECT id FROM estados_proyecto WHERE estado = "COMPLETADO")')
    proyectos = cursor.fetchall()
    conn.close()
    return render_template('sst/liquidacion_kari_form.html', proyectos=proyectos)

@app.route('/liquidacion-kari/<int:id>/aprobar', methods=['POST'])
@login_required
def aprobar_liquidacion_kari(id):
    estado = request.form['estado']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE liquidacion_kari SET estado_liquidacion = ?, aprobado_por = ?, fecha_aprobacion = ? WHERE id = ?', (estado, session['user_id'], datetime.now().strftime('%Y-%m-%d'), id))
    conn.commit()
    conn.close()
    flash(f'Liquidacion {estado}', 'success')
    return redirect(url_for('liquidacion_kari'))

# INFORME MENSUAL SST
@app.route('/informe-mensual-sst')
@login_required
def informe_mensual_sst():
    mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT a.*, u.nombre, u.rol FROM asistencia a JOIN usuarios u ON a.usuario_id = u.id WHERE strftime("%Y-%m", a.fecha) = ? ORDER BY a.fecha, u.nombre', (mes,))
    asistencias_mes = cursor.fetchall()
    cursor.execute('SELECT u.nombre, COUNT(CASE WHEN a.estado = "PRESENTE" THEN 1 END) as presentes, COUNT(CASE WHEN a.estado = "TARDANZA" THEN 1 END) as tardanzas, COUNT(CASE WHEN a.estado = "AUSENTE" THEN 1 END) as ausentes, COUNT(*) as total FROM usuarios u LEFT JOIN asistencia a ON u.id = a.usuario_id AND strftime("%Y-%m", a.fecha) = ? WHERE u.activo = 1 GROUP BY u.nombre ORDER BY u.nombre', (mes,))
    resumen_asistencia = cursor.fetchall()
    cursor.execute('SELECT a.*, u.nombre as usuario_nombre FROM ats a JOIN usuarios u ON a.usuario_id = u.id WHERE strftime("%Y-%m", a.fecha) = ? ORDER BY a.fecha DESC', (mes,))
    ats_mes = cursor.fetchall()
    cursor.execute('SELECT c.*, u.nombre as instructor_nombre FROM charlas_sst c JOIN usuarios u ON c.instructor_id = u.id WHERE strftime("%Y-%m", c.fecha) = ? ORDER BY c.fecha DESC', (mes,))
    charlas_mes = cursor.fetchall()
    cursor.execute('SELECT e.*, u.nombre as usuario_nombre FROM fotos_epps e JOIN usuarios u ON e.usuario_id = u.id WHERE strftime("%Y-%m", e.fecha) = ? ORDER BY e.fecha DESC', (mes,))
    epps_mes = cursor.fetchall()
    conn.close()
    return render_template('sst/informe_mensual.html', mes=mes, asistencias=asistencias_mes, resumen_asistencia=resumen_asistencia, ats_mes=ats_mes, charlas_mes=charlas_mes, epps_mes=epps_mes)

# ADMIN
@app.route('/admin/configuracion')
@login_required
@supervisor_required
def admin_configuracion():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_proyectos ORDER BY id')
    tipos = cursor.fetchall()
    cursor.execute('SELECT * FROM estados_proyecto ORDER BY id')
    estados = cursor.fetchall()
    cursor.execute('SELECT * FROM configuracion')
    config = cursor.fetchall()
    conn.close()
    return render_template('admin/configuracion.html', tipos=tipos, estados=estados, configuracion=config)

def seed_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    usuarios = [
        ('supervisor', hash_password('admin123'), 'Supervisor Planta Externa', 'supervisor', None),
        ('kari', hash_password('kari123'), 'Kari Rodriguez', 'asistente', None),
        ('mayer', hash_password('mayer123'), 'Mayer Bonilla', 'tecnico', 1),
        ('raul', hash_password('raul123'), 'Raul Lapa', 'tecnico', 1),
        ('cesar', hash_password('cesar123'), 'Cesar Armuto', 'tecnico', 2),
        ('diego', hash_password('diego123'), 'Diego Lopez', 'tecnico', 2),
    ]
    cursor.executemany('INSERT INTO usuarios (username, password_hash, nombre, rol, cuadrilla_id) VALUES (?, ?, ?, ?, ?)', usuarios)
    equipos = [
        ('cuadrilla', 'Cuadrilla 1', 'Mayer Bonilla', 'Raul Lapa', 'activo', None, None, 92, 'Excelente rendimiento'),
        ('cuadrilla', 'Cuadrilla 2', 'Cesar Armuto', 'Diego Lopez', 'activo', None, None, 88, 'Buen rendimiento'),
        ('contratista', 'GKA', '', '', 'activo', None, None, 85, 'Contratista externo'),
        ('contratista', 'G&E', '', '', 'activo', None, None, 80, 'Contratista externo'),
        ('contratista', 'JOV', '', '', 'activo', None, None, 75, 'Contratista externo'),
        ('administrativo', 'Asistente', 'Kari Rodriguez', '', 'activo', None, None, 95, 'Coordinacion administrativa'),
    ]
    cursor.executemany('INSERT INTO equipos (tipo, nombre, miembro1, miembro2, estado, proyecto_actual_id, disponible_desde, rendimiento, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', equipos)
    tipos = [
        ('FTTH', 'Fibra Optica al Hogar', 'Proyectos de instalacion de red FTTH nuevos'),
        ('AN', 'Ampliaciones Nuevas', 'Ampliaciones de cobertura en zonas existentes'),
        ('TFO', 'Tendido Fibra Optica', 'Troncales y tendidos de fibra optica'),
        ('CORP', 'Corporativos', 'Instalacion de clientes corporativos'),
        ('CCOM', 'Clientes Comerciales', 'Instalacion de clientes comerciales'),
        ('EVTEM', 'Eventos Deportivos', 'Instalaciones temporales para eventos deportivos'),
        ('RTP', 'Retiro Red Programado', 'Retiro de equipos y materiales de clientes'),
        ('MRE', 'Mantenimiento Emergencia', 'Mantenimiento de red por emergencia'),
        ('MRP', 'Mantenimiento Programado', 'Mantenimiento preventivo de red'),
        ('OTROS', 'Otros Proyectos', 'Apoyos a RDC y proyectos varios'),
    ]
    cursor.executemany('INSERT INTO tipos_proyectos (prefijo, nombre, descripcion) VALUES (?, ?, ?)', tipos)
    estados = [
        ('PENDIENTE', 'GRIS', 'Proyecto creado, pendiente de asignacion'),
        ('EN PROCESO', 'AMARILLO', 'Proyecto en ejecucion'),
        ('COMPLETADO', 'VERDE', 'Proyecto finalizado y aprobado'),
        ('CON OBSERVACIONES', 'NARANJA', 'Proyecto con observaciones pendientes'),
        ('RETRASADO', 'ROJO', 'Proyecto con retraso en ejecucion'),
    ]
    cursor.executemany('INSERT INTO estados_proyecto (estado, color_semaforo, descripcion) VALUES (?, ?, ?)', estados)
    cursor.execute('SELECT id FROM estados_proyecto WHERE estado = "EN PROCESO"')
    estado_en_proceso = cursor.fetchone()['id']
    cursor.execute('SELECT id FROM estados_proyecto WHERE estado = "COMPLETADO"')
    estado_completado = cursor.fetchone()['id']
    cursor.execute('SELECT id FROM estados_proyecto WHERE estado = "PENDIENTE"')
    estado_pendiente = cursor.fetchone()['id']
    proyectos = [
        ('FTTH-001-2026', 1, 1, 2026, 'Proyecto FTTH - Zona Ate Vitarte', 'Calle Los Pinos', 'Ate', estado_en_proceso, '2026-01-01', '2026-02-15', None, 3, None, 45, 50000, 'PENDIENTE', 'PENDIENTE', 'En construccion', 1),
        ('AN-001-2026', 2, 1, 2026, 'Ampliacion Zona La Molina', 'Av. La Molina', 'La Molina', estado_pendiente, '2026-01-05', '2026-02-20', None, 4, None, 0, 35000, 'PENDIENTE', 'PENDIENTE', 'Pendiente de asignacion', 1),
        ('TFO-001-2026', 3, 1, 2026, 'Troncal Principal Av. Javier Prado', 'Av. Javier Prado', 'San Borja', estado_en_proceso, '2026-01-10', '2026-02-28', None, None, 3, 60, 80000, 'PENDIENTE', 'PENDIENTE', 'Tendido en progreso', 1),
        ('CORP-001-2026', 4, 1, 2026, 'Instalacion Empresa ABC S.A.C.', 'Calle Las Flores 123', 'Miraflores', estado_completado, '2026-01-15', '2026-01-25', '2026-01-24', 5, None, 100, 15000, 'APROBADO', 'VERDE', 'Proyecto finalizado sin observaciones', 1),
        ('CCOM-001-2026', 5, 1, 2026, 'Hostal Los Pinos', 'Av. Los Pinos 456', 'Surco', estado_en_proceso, '2026-01-20', '2026-02-05', None, 6, None, 70, 8000, 'PENDIENTE', 'PENDIENTE', 'Instalacion de equipos', 1),
    ]
    cursor.executemany('INSERT INTO proyectos (codigo, tipo_id, numero, anio, nombre, ubicacion, zona_distrito, estado_id, fecha_inicio, fecha_fin_estimada, fecha_fin_real, responsable_id, contratista_id, avance, costo_estimado, certificacion_estado, plano_semaforo, observaciones, creado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', proyectos)
    asistencias = [
        ('2026-06-12', 3, '07:30', '17:00', 'PRESENTE', 'Entrada puntual', 1),
        ('2026-06-12', 4, '07:35', '17:00', 'PRESENTE', 'Entrada puntual', 1),
        ('2026-06-12', 5, '08:00', '17:00', 'TARDANZA', 'Llego tarde por trafico', 1),
        ('2026-06-12', 6, '07:45', '17:00', 'PRESENTE', 'Entrada puntual', 1),
        ('2026-06-12', 2, '08:00', '17:00', 'PRESENTE', 'Asistente administrativa', 1),
    ]
    cursor.executemany('INSERT INTO asistencia (fecha, usuario_id, hora_entrada, hora_salida, estado, observaciones, registrado_por) VALUES (?, ?, ?, ?, ?, ?, ?)', asistencias)
    ats_ejemplo = [
        (1, '2026-06-10', 3, 'Tendido de fibra optica en postes', 'Caida de postes, contacto con cables electricos', 'Uso de arnes, distancia minima 3m de cables electricos', 'CASCO, CHALECO, GUANTES, ARNES', 'PENDIENTE', None, None, 'Pendiente de aprobacion supervisor'),
        (4, '2026-06-08', 5, 'Instalacion de equipos en rack', 'Corte por herramientas, golpes', 'Uso de guantes, lentes de seguridad', 'CASCO, CHALECO, GUANTES, LENTES', 'APROBADO', 1, '2026-06-08', 'Aprobado para ejecucion'),
    ]
    cursor.executemany('INSERT INTO ats (proyecto_id, fecha, usuario_id, actividad, riesgos_identificados, medidas_preventivas, epp_requeridos, estado, aprobado_por, fecha_aprobacion, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', ats_ejemplo)
    charlas = [
        ('2026-06-10', 'Uso correcto del arnes de seguridad', 1, 5, 'Mayer Bonilla, Raul Lapa, Cesar Armuto, Diego Lopez', 4, None, 'Revision de puntos de anclaje, ajuste correcto, inspeccion antes de uso', 'REALIZADA'),
        ('2026-06-05', 'Identificacion de riesgos electricos', 1, 5, 'Mayer Bonilla, Raul Lapa, Cesar Armuto', 3, None, 'Distancia de seguridad, senalizacion, uso de guantes dielectricos', 'REALIZADA'),
    ]
    cursor.executemany('INSERT INTO charlas_sst (fecha, tema, instructor_id, duracion_minutos, asistentes, cantidad_asistentes, evidencia_foto_url, resumen, estado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', charlas)
    config = [
        ('anio_actual', '2026', 'Anio en curso'),
        ('correlativo_ftth', '1', 'Ultimo FTTH'),
        ('correlativo_an', '1', 'Ultimo AN'),
        ('correlativo_tfo', '1', 'Ultimo TFO'),
    ]
    cursor.executemany('INSERT INTO configuracion (parametro, valor, descripcion) VALUES (?, ?, ?)', config)
    conn.commit()
    conn.close()
    print("Datos de ejemplo V2 cargados")

if __name__ == '__main__':
    os.makedirs('uploads/evidencias', exist_ok=True)
    os.makedirs('uploads/epps', exist_ok=True)
    os.makedirs('uploads/ats', exist_ok=True)
    os.makedirs('uploads/charlas', exist_ok=True)
    os.makedirs('uploads/planos', exist_ok=True)
    os.makedirs('database', exist_ok=True)
    init_db()
    seed_data()
    print("=" * 70)
    print("SISTEMA DE GESTION V2 - CABLEVISION PERU")
    print("Planta Externa + SST (Seguridad y Salud en el Trabajo)")
    print("=" * 70)
    print("Iniciando servidor...")
    print("Accede a: http://localhost:5000")
    print("Usuario: supervisor | Password: admin123")
    print("=" * 70)
    app.run(debug=True, host='0.0.0.0', port=5000)
