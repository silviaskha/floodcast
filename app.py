from flask import Flask, request, render_template, flash, redirect, url_for, jsonify, session
import joblib
import mysql.connector
from datetime import date, datetime
from datetime import timedelta
 

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Inisialisasi model dan scaler
try:
    # Model dan scaler untuk Kalimas
    model = joblib.load('model/knn_model_banjir.pkl')
    scaler = joblib.load('model/scaler_banjir.pkl')

    # Model dan scaler untuk Nil
    model2 = joblib.load('model/knn_model_nil.pkl')
    scaler2 = joblib.load('model/scaler_nil.pkl')

    # Model dan scaler untuk Batu
    model3 = joblib.load('model/model_batu.pkl')
    scaler3 = joblib.load('model/scaler_batu.pkl')

    print("Model dan Scaler berhasil di-load.")

except FileNotFoundError:
    model = None
    scaler = None
    model2 = None
    scaler2 = None
    model3 = None
    scaler3 = None

    print("File model atau scaler tidak ditemukan.")

# Mengatur koneksi database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="try_floodcast",
    port=3306
)


@app.route("/")
def main():
    cursor = db.cursor(dictionary=True)
    
    # Ambil daftar lokasi untuk dropdown
    cursor.execute("SELECT * FROM lokasi")
    lokasi_list = cursor.fetchall()
    
    # Ambil lokasi yang dipilih dari parameter URL
    selected_lokasi = request.args.get('location')
    
    # Jika tidak ada lokasi yang dipilih, gunakan lokasi pertama
    if not selected_lokasi and lokasi_list:
        selected_lokasi = lokasi_list[0]['nama_lokasi']
    
    # Inisialisasi variabel default
    latest_data = None
    flowmeter_time = []
    flowmeter_values = []
    rainfall_time = []
    rainfall_intensity = []
    
    if selected_lokasi:
        # Ambil tanggal hari ini
        today = datetime.now().date()
        
        # Query data prediksi terbaru untuk tanggal hari ini dan lokasi yang dipilih
        cursor.execute("""
            SELECT dp.* 
            FROM dataprediksi dp
            JOIN lokasi l ON dp.lokasi_id = l.id
            WHERE l.nama_lokasi = %s AND dp.tanggal = %s
            ORDER BY dp.jam DESC
            LIMIT 1
        """, (selected_lokasi, today))
        latest_data = cursor.fetchone()
        
        # Jika ada data prediksi untuk hari ini
        if latest_data:
            # Query data flowmeter untuk chart
            cursor.execute("""
                SELECT dp.jam, dp.flowmeter 
                FROM dataprediksi dp
                JOIN lokasi l ON dp.lokasi_id = l.id
                WHERE dp.tanggal = %s AND l.nama_lokasi = %s 
                ORDER BY dp.jam ASC
            """, (today, selected_lokasi))
            flowmeter_data = cursor.fetchall()
            
            # Persiapkan data flowmeter untuk chart
            flowmeter_time = [str(data['jam']) for data in flowmeter_data]
            flowmeter_values = [float(data['flowmeter']) for data in flowmeter_data]
            
            # Query data curah hujan untuk chart
            cursor.execute("""
                SELECT dp.jam, dp.curah_hujan 
                FROM dataprediksi dp
                JOIN lokasi l ON dp.lokasi_id = l.id
                WHERE dp.tanggal = %s AND l.nama_lokasi = %s 
                ORDER BY dp.jam ASC
            """, (today, selected_lokasi))
            rainfall_data = cursor.fetchall()
            
            # Persiapkan data curah hujan untuk chart
            rainfall_time = [str(data['jam']) for data in rainfall_data]
            rainfall_intensity = [float(data['curah_hujan']) for data in rainfall_data]
    
    return render_template('dashboard.html', 
                           latest_data=latest_data,
                           lokasi_list=lokasi_list, 
                           selected_lokasi=selected_lokasi,
                           flowmeter_time=flowmeter_time,
                           flowmeter_values=flowmeter_values,
                           rainfall_time=rainfall_time,
                           rainfall_intensity=rainfall_intensity,
                           title_page="Dashboard"
                           )


# LOGIN halaman system
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        
        # Check if the user exists in the 'admin' table
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username = %s AND password = %s", 
                       (username, password))
        admin = cursor.fetchone()
        cursor.close()
        
        if admin:
            session['admin'] = admin['username']  # Store admin info in session
            return redirect(url_for('system_admin'))  # Redirect to system-admin
        else:
            return render_template('login.html', error="Invalid username or password.")
    
    return render_template('login.html', error='')

@app.route('/logout')
def logout():
    session.pop('admin', None)  # Remove admin session on logout
    return redirect(url_for('main'))  # Redirect to home page



@app.route("/debit-aliran", methods=['GET', 'POST'])
def debitaliran():
    # Buat cursor untuk query database
    cursor = db.cursor(dictionary=True)
    
    # Ambil daftar lokasi
    cursor.execute("SELECT id, nama_lokasi FROM lokasi")
    lokasi_list = cursor.fetchall()
    
    # Default tanggal hari ini
    today = date.today()
    
    # Default lokasi pertama (index 0)
    default_lokasi = lokasi_list[0] if lokasi_list else None
    
    # Variabel untuk menyimpan data grafik
    grafik_data = []
    pesan_error = None
    tanggal_dipilih = today
    lokasi_dipilih = default_lokasi
    
    # Jika ada request POST (form submit)
    if request.method == 'POST':
        # Ambil lokasi dan tanggal dari form
        lokasi_id = request.form.get('lokasi')
        tanggal_input = request.form.get('tanggal')
        
        # Konversi tanggal input ke format DATE
        try:
            if tanggal_input:
                tanggal_dipilih = datetime.strptime(tanggal_input, '%Y-%m-%d').date()
            else:
                tanggal_dipilih=today
        except (ValueError, TypeError):
            tanggal = today
        
        # Cari lokasi yang dipilih
        lokasi_dipilih = next((loc for loc in lokasi_list if str(loc['id']) == str(lokasi_id)), default_lokasi)
        

        # Query untuk mendapatkan data curah hujan
        cursor.execute("""
            SELECT jam, flowmeter 
            FROM dataprediksi 
            WHERE lokasi_id = %s AND tanggal = %s 
            ORDER BY jam
        """, (lokasi_dipilih['id'], tanggal_dipilih))
        
        grafik_data = cursor.fetchall()
        
        # Cek apakah data tersedia
        if not grafik_data:
            pesan_error = f"Tidak ada data debit aliran untuk lokasi {lokasi_dipilih['nama_lokasi']} pada tanggal {tanggal_dipilih}"
    else:
        # Default saat pertama kali load halaman
        if default_lokasi:
            # Query data untuk lokasi default dan tanggal hari ini
            cursor.execute("""
                SELECT jam, flowmeter 
                FROM dataprediksi 
                WHERE lokasi_id = %s AND tanggal = %s 
                ORDER BY jam
            """, (default_lokasi['id'], today))
            
            grafik_data = cursor.fetchall()
            
            # Cek apakah data tersedia
            if not grafik_data:
                pesan_error = f"Tidak ada data curah hujan untuk lokasi {default_lokasi['nama_lokasi']} pada tanggal {today}"
    
    # Tutup cursor
    cursor.close()

    title_page=''
    
    return render_template('debit-aliran.html', 
                           lokasi_list=lokasi_list, 
                           grafik_data=grafik_data, 
                           tanggal=tanggal_dipilih,
                           lokasi_dipilih=lokasi_dipilih,
                           default_lokasi=default_lokasi,
                           pesan_error=pesan_error,
                           title_page="Grafik Debit Aliran")

@app.route("/curah-hujan", methods=['GET', 'POST'])
def curahhujan():
    # Buat cursor untuk query database
    cursor = db.cursor(dictionary=True)
    
    # Ambil daftar lokasi
    cursor.execute("SELECT id, nama_lokasi FROM lokasi")
    lokasi_list = cursor.fetchall()
    
    # Default tanggal hari ini
    today = date.today()
    
    # Default lokasi pertama (index 0)
    default_lokasi = lokasi_list[0] if lokasi_list else None
    
    # Variabel untuk menyimpan data grafik
    grafik_data = []
    pesan_error = None
    tanggal_dipilih = today
    lokasi_dipilih = default_lokasi
    
    # Jika ada request POST (form submit)
    if request.method == 'POST':
        # Ambil lokasi dan tanggal dari form
        lokasi_id = request.form.get('lokasi')
        tanggal_input = request.form.get('tanggal')
        
        # Konversi tanggal input ke format DATE
        try:
            if tanggal_input:
                tanggal_dipilih = datetime.strptime(tanggal_input, '%Y-%m-%d').date()
            else:
                tanggal_dipilih=today
        except (ValueError, TypeError):
            tanggal = today
        
        # Cari lokasi yang dipilih
        lokasi_dipilih = next((loc for loc in lokasi_list if str(loc['id']) == str(lokasi_id)), default_lokasi)
        

        # Query untuk mendapatkan data curah hujan
        cursor.execute("""
            SELECT jam, curah_hujan 
            FROM dataprediksi 
            WHERE lokasi_id = %s AND tanggal = %s 
            ORDER BY jam
        """, (lokasi_dipilih['id'], tanggal_dipilih))
        
        grafik_data = cursor.fetchall()
        
        # Cek apakah data tersedia
        if not grafik_data:
            pesan_error = f"Tidak ada data curah hujan untuk lokasi {lokasi_dipilih['nama_lokasi']} pada tanggal {tanggal_dipilih}"
    else:
        # Default saat pertama kali load halaman
        if default_lokasi:
            # Query data untuk lokasi default dan tanggal hari ini
            cursor.execute("""
                SELECT jam, curah_hujan 
                FROM dataprediksi 
                WHERE lokasi_id = %s AND tanggal = %s 
                ORDER BY jam
            """, (default_lokasi['id'], today))
            
            grafik_data = cursor.fetchall()
            
            # Cek apakah data tersedia
            if not grafik_data:
                pesan_error = f"Tidak ada data curah hujan untuk lokasi {default_lokasi['nama_lokasi']} pada tanggal {today}"
    
    # Tutup cursor
    cursor.close()
    
    title_page=''

    return render_template('curah-hujan.html', 
                           lokasi_list=lokasi_list, 
                           grafik_data=grafik_data, 
                           tanggal=tanggal_dipilih,
                           default_lokasi=default_lokasi,
                           lokasi_dipilih=lokasi_dipilih,
                           pesan_error=pesan_error,
                           title_page="Grafik Curah Hujan"
                           )

@app.route("/dataprediksi",  methods=['GET', 'POST'])
def dataprediksi():
    lokasi_list = []
    lokasi_id_selected = None
    lokasi_name_selected = None
    prediksi_list = []
    tanggal_selected = None  # Tanggal yang dipilih
    error = None

    try:
        # Ambil daftar lokasi dari database
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT id, nama_lokasi FROM lokasi")
        lokasi_list = cursor.fetchall()

        if request.method == 'POST':
            # Tangkap lokasi_id dan tanggal dari form
            lokasi_id_selected = request.form.get('lokasi_id')
            tanggal_selected = request.form.get('tanggal')

            if lokasi_id_selected:
                # Ambil nama lokasi yang dipilih
                cursor.execute(
                    "SELECT nama_lokasi FROM lokasi WHERE id = %s", 
                    (lokasi_id_selected,)
                )
                lokasi_name_selected = cursor.fetchone()[0]

                # Ambil data prediksi berdasarkan lokasi dan tanggal yang dipilih
                if tanggal_selected:
                    cursor.execute(
                        """
                        SELECT tanggal, jam, curah_hujan, flowmeter, inclinometer, output 
                        FROM dataprediksi 
                        WHERE lokasi_id = %s AND tanggal = %s
                        """,
                        (lokasi_id_selected, tanggal_selected)
                    )
                else:
                    # Jika tanggal tidak dipilih, ambil semua data berdasarkan lokasi
                    cursor.execute(
                        """
                        SELECT tanggal, jam, curah_hujan, flowmeter, inclinometer, output 
                        FROM dataprediksi 
                        WHERE lokasi_id = %s
                        """,
                        (lokasi_id_selected,)
                    )
                prediksi_list = cursor.fetchall()
            else:
                error = "Pilih lokasi terlebih dahulu."
    except Exception as e:
        error = f"Terjadi kesalahan: {str(e)}"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

    title_page=''

    return render_template(
        'dataprediksi.html',
        lokasi_list=lokasi_list,
        lokasi_id_selected=lokasi_id_selected,
        lokasi_name_selected=lokasi_name_selected,
        prediksi_list=prediksi_list,
        tanggal_selected=tanggal_selected,  # Kirim tanggal yang dipilih ke template
        error=error, title_page="Data  Prediksi"
    )


@app.route("/status-device")
def statusdevice():
    title_page='' 
    return render_template('status-device.html', title_page="IoT Device")


#  System-admin
@app.route("/system-admin")
def system_admin():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    # Ambil data admin
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admin")
    daftar_admin = cursor.fetchall()
    
    # Ambil data lokasi
    cursor.execute("SELECT id, nama_lokasi FROM lokasi")
    daftar_lokasi = cursor.fetchall()
    
    # Ambil prediksi terbaru dari session
    recent_prediction = session.get('recent_prediction', None)

    title_page=''

    return render_template('system-admin.html',
                           username=session['admin'],
                           daftar_admin=daftar_admin,
                           daftar_lokasi=daftar_lokasi,
                           recent_prediction=recent_prediction,
                           title_page="Sytem - Admin"
                           )

# Card Tambah admin
@app.route("/add-admin", methods=['POST'])
def add_admin():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    try:
        cursor = db.cursor()
        cursor.execute("INSERT INTO admin (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
        db.commit()
        flash("Admin berhasil ditambahkan!", "success")
    except mysql.connector.Error as err:
        flash(f"Error: {err}", "danger")
    
    return redirect(url_for('system_admin'))

# Card Hapus admin
@app.route("/delete-admin", methods=['POST'])
def delete_admin():
    admin_id = request.form['admin_id']
    
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM admin WHERE id = %s", (admin_id,))
        db.commit()
        flash("Admin berhasil dihapus!", "success")
    except mysql.connector.Error as err:
        flash(f"Error: {err}", "danger")
    
    return redirect(url_for('system_admin'))

# Card Tambah lokasi
@app.route("/add-location", methods=['POST'])
def add_location():
    nama_lokasi = request.form['nama-lokasi']
    
    try:
        cursor = db.cursor()
        cursor.execute("INSERT INTO lokasi (nama_lokasi) VALUES (%s)", (nama_lokasi,))
        db.commit()
        flash("Lokasi berhasil ditambahkan!", "success")
    except mysql.connector.Error as err:
        flash(f"Error: {err}", "danger")
    
    return redirect(url_for('system_admin'))

# Card Coba Prediksi
@app.route("/trypredict", methods=['POST'])
def trypredict():
    lokasi_id = int(request.form['lokasi_id'])
    curah_hujan = float(request.form['curah_hujan'])
    flowmeter = float(request.form['flowmeter'])
    inclinometer = float(request.form['inclinometer'])
    save_to_db = 'save_to_db' in request.form

    # Pilih model dan scaler
    if lokasi_id == 1:
        selected_model = model
        selected_scaler = scaler
        lokasi_name = "Sungai Kalimas"
    elif lokasi_id == 2:
        selected_model = model2
        selected_scaler = scaler2
        lokasi_name = "Sungai Bengawan Solo"
    elif lokasi_id == 3:
        selected_model = model3
        selected_scaler = scaler3
        lokasi_name = "Batu, Kec. Bumiaji Malang"
    else:
        flash("Model dan scaler tidak tersedia untuk lokasi ini.", "warning")
        return redirect(url_for('system_admin'))

    # Jika tidak ada model atau scaler
    if not selected_model or not selected_scaler:
        flash("Model atau scaler tidak tersedia untuk lokasi ini.", "danger")
        return redirect(url_for('system_admin'))

    try:
        # Prediksi
        scaled_data = selected_scaler.transform([[curah_hujan, flowmeter, inclinometer]])
        prediction = selected_model.predict(scaled_data)
        hasil_prediksi = "Berpotensi Banjir" if prediction[0] == 0 else "Tidak Berpotensi Banjir"


        if save_to_db:
            tanggal = datetime.now().date()
            jam = datetime.now().time()
            
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO dataprediksi (tanggal, jam, curah_hujan, flowmeter, inclinometer, output, lokasi_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (tanggal, jam, curah_hujan, flowmeter, inclinometer, hasil_prediksi, lokasi_id))
            db.commit()
            flash("Data Tersimpan di database", "success")
            return redirect(url_for('system_admin'))


        # Simpan data inputan sementara di session
        session['recent_prediction'] = {
            'lokasi': lokasi_name,
            'curah_hujan': curah_hujan,
            'flowmeter': flowmeter,
            'inclinometer': inclinometer,
            'output': hasil_prediksi
        }

    except Exception as e:
        flash(f"Terjadi kesalahan saat prediksi: {e}", "danger")

    

    return redirect(url_for('system_admin'))


# HTML TESTING

#########

if __name__ == '__main__':
    app.run(debug=True)
