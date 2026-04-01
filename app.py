import os, math, random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth

directorio_base = os.path.dirname(os.path.abspath(__file__))
ruta_env = os.path.join(directorio_base, '.env')

try:
    with open(ruta_env, 'r', encoding='utf-8') as archivo:
        print("📜 CONTENIDO BRUTO DEL ARCHIVO:")
        print(archivo.read())
        print("-------------------------------")
except Exception as e:
    print("❌ ERROR LEYENDO EL ARCHIVO:", e)

load_dotenv(ruta_env, override=True)

print("🕵️‍♂️ PRUEBA DE ID:", os.getenv("GOOGLE_CLIENT_ID"))

app = Flask(__name__)
app.secret_key = '123SDXWER@234**ÑDS234'
serializer = URLSafeTimedSerializer(app.secret_key)

# Configuración de la base de datos (se creará un archivo datos.db)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///datos.db'
db = SQLAlchemy(app)

# 2. Configuramos la herramienta OAuth
oauth = OAuth(app)

# 3. Registramos a Google usando las llaves de nuestra caja fuerte
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    # Esta URL le dice a Authlib dónde encontrar las reglas de seguridad de Google
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    # Le pedimos a Google que nos envíe el perfil y el correo del usuario
    client_kwargs={'scope': 'openid email profile'}
)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    # El correo es obligatorio y único para evitar cuentas duplicadas
    correo = db.Column(db.String(120), unique=True, nullable=False) 
    # La contraseña es opcional (estará vacía si el usuario entra con Google)
    password = db.Column(db.String(200), nullable=True) 
    estatura_cm = db.Column(db.Float, nullable=True)
    pesos = db.relationship('RegistroPeso', backref='usuario_rel', lazy=True)

class RegistroPeso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    peso = db.Column(db.Float, nullable=False)
    imc = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=db.func.now())
    # NUEVO: La llave foránea que conecta este peso con un ID de usuario específico
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
# Crear la base de datos físicamente
with app.app_context():
    db.create_all()

# 1. La pantalla principal ahora es el Login
@app.route('/')
def inicio():
    return render_template('login.html')

# 2. Movemos el registro a su propia ruta
@app.route('/registro')
def registro():
    return render_template('registro_perfil.html')

@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        correo_ingresado = request.form.get('email')
        usuario = Usuario.query.filter_by(correo=correo_ingresado).first()
        
        if usuario:
            token = serializer.dumps(correo_ingresado, salt='recuperacion-pass')
            enlace = url_for('reset_password', token=token, _external=True)
            
            print("\n" + "="*50)
            print(f"EMAIL DE RECUPERACIÓN PARA: {correo_ingresado}")
            print(f"HAZ CLIC AQUÍ: {enlace}")
            print("="*50 + "\n")
            
            flash('Si el correo existe en nuestra base, verás el enlace en la consola de Python.', 'success')
        else:
            flash('Si el correo existe en nuestra base, verás el enlace en la consola de Python.', 'success')
            
        return redirect(url_for('recuperar_password'))

    return render_template('recuperar.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        correo_token = serializer.loads(token, salt='recuperacion-pass', max_age=3600)
    except SignatureExpired:
        flash('El enlace ha expirado. Solicita uno nuevo.', 'error')
        return redirect(url_for('recuperar_password'))
    except:
        flash('Enlace inválido.', 'error')
        return redirect(url_for('recuperar_password'))

    if request.method == 'POST':
        nueva_password = request.form.get('password')
        usuario = Usuario.query.filter_by(correo=correo_token).first()
        
        if usuario:
            usuario.password = generate_password_hash(nueva_password)
            db.session.commit()
            flash('Tu contraseña ha sido actualizada correctamente. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('inicio'))
            
    return render_template('reset.html', token=token)

@app.route('/guardar_perfil', methods=['POST'])
def guardar_perfil():
    nombre_usuario = request.form['nombre']
    estatura_centimetros = float(request.form['estatura'])
    estatura_metros = estatura_centimetros / 100
    
    nuevo_usuario = Usuario(nombre=nombre_usuario, estatura_cm=estatura_metros)
    db.session.add(nuevo_usuario)
    db.session.commit()
    
    # ¡Esta es la línea clave que cambió! 
    return redirect(url_for('ver_panel'))

# ... (mantén tus clases Usuario y RegistroPeso arriba)

@app.route('/panel')
def ver_panel():
    if 'usuario_id' not in session:
        return redirect(url_for('inicio'))
    
    usuario_actual = db.session.get(Usuario, session['usuario_id'])
    registros = RegistroPeso.query.filter_by(usuario_id=usuario_actual.id).order_by(RegistroPeso.fecha.asc()).all()


    # 🌟 LISTA DE CELEBRIDADES (Altura en cm, Peso en kg)
    celebridades = [
    # --- AUTOMOVILISMO (F1 & RALLY) ---
    {"nombre": "Lewis Hamilton (F1)", "h": 174, "w": 73},
    {"nombre": "Max Verstappen (F1)", "h": 181, "w": 72},
    {"nombre": "Sébastien Ogier (Rally)", "h": 181, "w": 75},
    {"nombre": "Sébastien Loeb (Rally)", "h": 171, "w": 70},
    {"nombre": "Kalle Rovanperä (Rally)", "h": 175, "w": 68},
    {"nombre": "Charles Leclerc (F1)", "h": 180, "w": 69},
    {"nombre": "Fernando Alonso (F1)", "h": 171, "w": 68},

    # --- FIGURAS ARGENTINAS ---
    {"nombre": "Lionel Messi", "h": 170, "w": 72},
    {"nombre": "Diego Maradona (Prime)", "h": 165, "w": 70},
    {"nombre": "Manu Ginóbili", "h": 198, "w": 93},
    {"nombre": "Juan Martín del Potro", "h": 198, "w": 97},
    {"nombre": "Bizarrap", "h": 174, "w": 74},
    {"nombre": "Duki", "h": 177, "w": 82},
    {"nombre": "Wos", "h": 175, "w": 70},
    {"nombre": "Trueno", "h": 170, "w": 68},
    {"nombre": "Paulo Londra", "h": 183, "w": 80},

    # --- ATLETAS DE ÉLITE ---
    {"nombre": "Cristiano Ronaldo", "h": 187, "w": 83},
    {"nombre": "LeBron James", "h": 206, "w": 113},
    {"nombre": "Usain Bolt", "h": 195, "w": 94},
    {"nombre": "Mike Tyson (Prime)", "h": 178, "w": 100},
    {"nombre": "Saúl 'Canelo' Álvarez", "h": 173, "w": 76},
    {"nombre": "Conor McGregor", "h": 175, "w": 70},
    {"nombre": "Serena Williams", "h": 175, "w": 72},
    {"nombre": "Erling Haaland", "h": 194, "w": 88},

    # --- ACTORES Y ACCIÓN ---
    {"nombre": "Dwayne Johnson (The Rock)", "h": 196, "w": 118},
    {"nombre": "Arnold Schwarzenegger (Prime)", "h": 188, "w": 105},
    {"nombre": "Jason Momoa", "h": 193, "w": 97},
    {"nombre": "Chris Hemsworth (Thor)", "h": 190, "w": 91},
    {"nombre": "Chris Evans (Cap. América)", "h": 183, "w": 80},
    {"nombre": "Tom Cruise", "h": 170, "w": 68},
    {"nombre": "Tom Holland (Spider-Man)", "h": 173, "w": 65},
    {"nombre": "Henry Cavill (Superman)", "h": 185, "w": 92},
    {"nombre": "Zac Efron (Actual)", "h": 173, "w": 82},
    {"nombre": "Gal Gadot", "h": 178, "w": 58},
    {"nombre": "Scarlett Johansson", "h": 160, "w": 57},
    {"nombre": "Margot Robbie", "h": 168, "w": 56},
    {"nombre": "Hugh Jackman", "h": 188, "w": 85},
    {"nombre": "Vin Diesel", "h": 182, "w": 102},
    {"nombre": "Robert Downey Jr.", "h": 174, "w": 78},

    # --- VARIOS Y EXTREMOS ---
    {"nombre": "Peter Dinklage", "h": 135, "w": 50},
    {"nombre": "Danny DeVito", "h": 147, "w": 70},
    {"nombre": "Hafþór Júlíus Björnsson (La Montaña)", "h": 206, "w": 150},
    {"nombre": "Shaquille O'Neal", "h": 216, "w": 147},
    {"nombre": "Zendaya", "h": 178, "w": 55},
    {"nombre": "Bad Bunny", "h": 180, "w": 75},
    {"nombre": "Eminem", "h": 173, "w": 68},
    {"nombre": "Shakira", "h": 157, "w": 53},
    {"nombre": "The Weeknd", "h": 173, "w": 73},
    {"nombre": "Post Malone", "h": 184, "w": 84},
    {"nombre": "Drake", "h": 182, "w": 89},

        # --- PERSONAJES FICTICIOS (VIDEOJUEGOS Y CINE) ---
    # Resident Evil
    {"nombre": "Leon S. Kennedy (RE4)", "h": 180, "w": 75},
    {"nombre": "Chris Redfield (RE5/8)", "h": 190, "w": 98},
    {"nombre": "Jill Valentine (RE3 Remake)", "h": 166, "w": 55},
    {"nombre": "Albert Wesker", "h": 190, "w": 90},
    {"nombre": "Ada Wong", "h": 173, "w": 53},
    {"nombre": "Lady Dimitrescu", "h": 290, "w": 200}, # El extremo para alturas gigantes

    # The Last of Us
    {"nombre": "Joel Miller (TLOU)", "h": 180, "w": 85},
    {"nombre": "Ellie Williams (TLOU 2)", "h": 165, "w": 55},
    {"nombre": "Abby Anderson", "h": 173, "w": 78},

    # Soulslike & Acción
    {"nombre": "Sekiro (Wolf)", "h": 175, "w": 70},
    {"nombre": "Geralt de Rivia (The Witcher)", "h": 185, "w": 85},
    {"nombre": "Kratos (God of War)", "h": 198, "w": 115},
    {"nombre": "Master Chief (Sin armadura)", "h": 208, "w": 130},
    {"nombre": "Solid Snake (MGS)", "h": 182, "w": 75},

    # Superhéroes & Otros
    {"nombre": "Batman (Bruce Wayne)", "h": 188, "w": 95},
    {"nombre": "Superman (Clark Kent)", "h": 191, "w": 107},
    {"nombre": "Spider-Man (Peter Parker)", "h": 178, "w": 76},
    {"nombre": "Wolverine (Logan)", "h": 160, "w": 88}, # Bajito pero pesado/musculoso
    {"nombre": "Indiana Jones", "h": 185, "w": 80},
    {"nombre": "John Wick", "h": 185, "w": 84},
    {"nombre": "Lara Croft", "h": 168, "w": 55}
    ]

    gemelo = None
    if usuario_actual.estatura_cm and registros:
        peso_actual = registros[-1].peso
        altura_actual = usuario_actual.estatura_cm * 100 
        
        # 1. Calculamos la distancia para TODOS y la guardamos en una lista
        coincidencias = []
        for c in celebridades:
            distancia = math.sqrt((altura_actual - c['h'])**2 + (peso_actual - c['w'])**2)
            # Guardamos el famoso junto con su distancia
            coincidencias.append({"datos": c, "distancia": distancia})

        # 2. Ordenamos toda la lista de menor a mayor distancia
        coincidencias.sort(key=lambda x: x['distancia'])

        # 3. Tomamos los 5 más parecidos (el "Top 5")
        mejores_coincidencias = coincidencias[:5]

        # 4. Elegimos uno al azar de esos 5 para que vaya rotando
        seleccionado = random.choice(mejores_coincidencias)
        gemelo = seleccionado['datos']

    
    imc_actual = 0
    categoria = {"label": "Sin datos", "color": "gray", "bg": "bg-gray-100", "text": "text-gray-500"}

    if registros and usuario_actual.estatura_cm:
        imc_actual = registros[-1].imc
        
        # Clasificación oficial de la OMS
        if imc_actual < 18.5:
            categoria = {
            "label": "Bajo Peso", 
            "bg": "bg-cyan-100", "text": "text-cyan-700", "border": "border-cyan-500",
            "consejo": "Se recomienda priorizar una alimentación densa en nutrientes y consultar con un profesional para alcanzar un peso saludable de forma equilibrada."
        }
        elif 18.5 <= imc_actual < 25:
            categoria = {
                "label": "Peso Normal", 
                "bg": "bg-green-100", "text": "text-green-700", "border": "border-green-500",
                "consejo": "¡Estado óptimo! Mantener una dieta variada y realizar actividad física regular son las claves para conservar este equilibrio a largo plazo."
            }
        elif 25 <= imc_actual < 30:
            categoria = {
                "label": "Exceso de Peso", 
                "bg": "bg-yellow-100", "text": "text-yellow-700", "border": "border-yellow-500",
                "consejo": "Pequeños cambios diarios, como aumentar la ingesta de fibra y sumar caminatas, pueden ayudar a mejorar tu composición corporal."
            }
        elif 30 <= imc_actual < 35:
            categoria = {
                "label": "Obesidad Grado I", 
                "bg": "bg-orange-100", "text": "text-orange-700", "border": "border-orange-500",
                "consejo": "Es un buen momento para enfocarse en hábitos sostenibles. Reducir productos ultraprocesados y mantener la constancia en el movimiento es fundamental."
            }
        elif 35 <= imc_actual < 40:
            categoria = {
                "label": "Obesidad Grado II", 
                "bg": "bg-red-100", "text": "text-red-700", "border": "border-red-500",
                "consejo": "Se sugiere buscar asesoramiento profesional para diseñar un plan integral de salud y actividad física adaptado a tus necesidades actuales."
            }
        else: # Obesidad Grado III (> 40)
            categoria = {
                "label": "Obesidad Grado III", 
                "bg": "bg-purple-100", "text": "text-purple-700", "border": "border-purple-500",
                "consejo": "Tu salud es la prioridad. Te recomendamos consultar con un equipo médico para recibir un seguimiento cercano, seguro y especializado."
            }


    return render_template('panel.html', usuario=usuario_actual, registros=registros, gemelo=gemelo, celebridades=celebridades, imc=imc_actual, cat=categoria)

@app.route('/guardar_peso', methods=['POST'])
def guardar_peso():
    if 'usuario_id' not in session:
        return redirect(url_for('inicio'))
    
    usuario_id = session['usuario_id']
    peso = float(request.form.get('peso'))
    fecha_str = request.form.get('fecha')
    
    fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
    
    usuario = Usuario.query.get(usuario_id)
    estatura = usuario.estatura_cm
    imc = round(peso / (estatura * estatura), 2)
    
    nuevo_registro = RegistroPeso(
        usuario_id=usuario_id,
        peso=peso,
        fecha=fecha_dt,
        imc=imc
    )
    
    db.session.add(nuevo_registro)
    db.session.commit()
    
    return redirect(url_for('ver_panel'))

@app.route('/editar_perfil')
def editar_perfil():
    # 1. Verificamos la pulsera
    if 'usuario_id' not in session:
        return redirect(url_for('inicio'))
        
    # 2. Traemos al usuario correcto
    usuario_actual = Usuario.query.get(session['usuario_id'])
    return render_template('editar_perfil.html', usuario=usuario_actual)

@app.route('/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('inicio'))
        
    usuario_actual = Usuario.query.get(session['usuario_id'])
    
    usuario_actual.nombre = request.form['nombre']
    estatura_centimetros = float(request.form['estatura'])
    usuario_actual.estatura_cm = estatura_centimetros / 100
    
    db.session.commit()
    return redirect(url_for('ver_panel'))

@app.route('/borrar_peso/<int:id>')
def borrar_peso(id):
    # 1. Buscamos el registro exacto usando su ID
    registro_a_borrar = RegistroPeso.query.get(id)
    
    # 2. Si existe, le decimos a la base de datos que lo elimine
    if registro_a_borrar:
        db.session.delete(registro_a_borrar)
        db.session.commit()
        
    # 3. Volvemos al panel
    return redirect(url_for('ver_panel'))

@app.route('/guardar_registro', methods=['POST'])
def guardar_registro():
    nombre_nuevo = request.form['nombre']
    correo_nuevo = request.form['correo']
    password_nuevo = request.form['password']
    
    # 🔍 LA VALIDACIÓN: Buscamos si ya hay alguien con ese correo
    usuario_existente = Usuario.query.filter_by(correo=correo_nuevo).first()
    
    if usuario_existente:
        # Guardamos el mensaje en memoria
        flash("Ese correo ya está registrado. Por favor, inicia sesión.")
        # Lo recargamos en la misma página de registro
        return redirect(url_for('registro'))
    
    # Si el correo está libre, guardamos al nuevo usuario
    nuevo_usuario = Usuario(nombre=nombre_nuevo, correo=correo_nuevo, password=password_nuevo)
    db.session.add(nuevo_usuario)
    db.session.commit()
    
    # Lo enviamos a la pantalla de Login para que entre con su nueva cuenta
    return redirect(url_for('inicio'))

@app.route('/iniciar_sesion', methods=['POST'])
def iniciar_sesion():
    correo_ingresado = request.form['correo']
    password_ingresada = request.form['password']
    
    usuario = Usuario.query.filter_by(correo=correo_ingresado).first()
    
    if usuario and usuario.password == password_ingresada:
        # 🎟️ Le ponemos la pulsera guardando su ID en la memoria del navegador
        session['usuario_id'] = usuario.id 
        return redirect(url_for('ver_panel'))
    else:
        flash("Datos incorrectos. Por favor, intenta de nuevo.")
        # Lo recargamos en la misma página de login
        return redirect(url_for('inicio'))

@app.route('/cerrar_sesion')
def cerrar_sesion():
    # El método .pop() "saca" o elimina el dato de la memoria de la sesión
    session.pop('usuario_id', None)
    
    # Una vez borrada la pulsera, lo enviamos a la pantalla de Login
    return redirect(url_for('inicio'))

@app.route('/login_google')
def login_google():
    ruta_de_regreso = url_for('callback', _external=True) 
    return google.authorize_redirect(ruta_de_regreso)


@app.route('/callback')
def callback():
    token = google.authorize_access_token()
    info_usuario = token.get('userinfo')
    
    correo_google = info_usuario['email']
    nombre_google = info_usuario['name']
    
    usuario = Usuario.query.filter_by(correo=correo_google).first()
    
    if not usuario:
        usuario = Usuario(nombre=nombre_google, correo=correo_google) # Sin password
        db.session.add(usuario)
        db.session.commit()
        flash(f"¡Bienvenido a Nutrisoft, {nombre_google}! Tu cuenta ha sido creada con Google.")
    
    session['usuario_id'] = usuario.id
    
    return redirect(url_for('ver_panel'))

@app.route('/soporte')
def soporte():
    # Si el usuario está logueado, le pasamos sus datos para la Navbar
    usuario_actual = None
    if 'usuario_id' in session:
        usuario_actual = db.session.get(Usuario, session['usuario_id'])
    
    return render_template('soporte.html', usuario=usuario_actual)

@app.route('/privacidad')
def privacidad():
    # Verificamos si hay un usuario logueado para adaptar la barra de navegación
    usuario_actual = None
    if 'usuario_id' in session:
        usuario_actual = db.session.get(Usuario, session['usuario_id'])
    
    return render_template('privacidad.html', usuario=usuario_actual)

@app.route('/terminos')
def terminos():
    usuario_actual = None
    if 'usuario_id' in session:
        usuario_actual = db.session.get(Usuario, session['usuario_id'])
    
    return render_template('terminos.html', usuario=usuario_actual)

@app.route('/logout')
def logout():
    # 🚪 Cerramos la sesión borrando el ID del usuario
    session.pop('usuario_id', None)
    # 📢 Avisamos al usuario y mandamos al login
    # IMPORTANTE: Cambia 'inicio' por el nombre de tu función de login
    flash("Has cerrado sesión correctamente.")
    return redirect(url_for('inicio'))

if __name__ == '__main__':
    app.run(debug=True)