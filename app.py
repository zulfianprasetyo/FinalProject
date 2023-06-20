import os
import locale
from os.path import join, dirname
from dotenv import load_dotenv

from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta
import hashlib
from bson import ObjectId
from flask import (
    Flask,
    flash,
    render_template,
    jsonify,
    request,
    redirect,
    session,
    send_file,
    url_for
)
from werkzeug.utils import secure_filename
from functools import wraps

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
SECRET_KEY = SECRET_KEY

locale.setlocale(locale.LC_ALL, 'id_ID')

app = Flask(__name__)
app.secret_key = 'Kelompok4'

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = './static/profile_pics'


TOKEN_KEY = 'tokenkel4'


@app.route("/")
def home():
    return render_template("home.html", session=session)


@app.route("/login", methods=['GET'])
def form_login():
    for i in db.user.find():
        print(i)
    return render_template("login_regis_user.html")


@app.route("/daftar", methods=['POST'])
def daftar():
    name = request.form['nama_lengkap']
    user_name = request.form['user_name']
    password = request.form['password']
    email = request.form['email']

    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    fotoKTP = request.files['fotoKTP']
    extension = fotoKTP.filename.split('.')[-1]
    fotoKTP_name = f'static/foto_validasi/fotoKTP-{mytime}.{extension}'
    fotoKTP.save(fotoKTP_name)

    fotoKK = request.files['fotoKK']
    extension = fotoKK.filename.split('.')[-1]
    fotoKK_name = f'static/foto_validasi/fotoKK-{mytime}.{extension}'
    fotoKK.save(fotoKK_name)

    fotoWajahKTP = request.files['fotoWajahKTP']
    extension = fotoWajahKTP.filename.split('.')[-1]
    fotoWajahKTP_name = f'static/foto_validasi/fotoWajahKTP-{mytime}.{extension}'
    fotoWajahKTP.save(fotoWajahKTP_name)

    level = 2

    check = db.user.find_one({"username": user_name})
    if check is not None:
        return 'username sudah digunakan'

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    db.user.insert_one({
        'fotoKTP': fotoKTP_name,
        'fotoKK': fotoKK_name,
        'fotoWajahKTP': fotoWajahKTP_name,
        'fotoProfil': '/static/profile_placeholder.png',
        'fotoSampul': '/static/imgs/gambar1.jpg',
        'username': user_name,
        'password': hashed_password,
        'nama': name,
        'email': email,
        'level': level,
        'status': 'pending'
    })
    flash('Pendaftaran Berhasil!')
    return redirect(url_for("login"))


@app.route("/login", methods=['POST'])
def login():
    username = request.form['user']
    password = request.form['password']

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    user = db.user.find_one({
        'username': username,
        'password': hashed_password,
        'level': 2,
    })

    if user:
        if user['status'] == 'verified':
            payload = {
                'nama': user['nama'],
                'username': user['username'],
                "email": user['email'],
                'level': user['level']
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
            session["token"] = token
            session["isLogin"] = True
            session["user"] = {
                "name": user['nama'],
                "username": user['username'],
                "email": user['email'],
                "fotoProfil": user['fotoProfil'],
                "fotoSampul": user['fotoSampul'],
                "level": user['level']
            }
            return redirect(url_for("home"))
        elif user['status'] == 'pending':
            return 'Akun belum diverifikasi oleh admin. Harap tunggu.'
    else:
        return 'Username atau password salah.'


@app.route("/login_admin", methods=['GET'])
def form_admin():
    return render_template("login_admin.html")


@app.route("/login_admin", methods=['POST'])
def login_admin():
    username = request.form['admin']
    password = request.form['password']

    cari = db.user.find_one({
        'username': username,
        'password': password,
        'level': 1
    })

    if not cari:
        return "<script>alert('Akun tidak ditemukan'); location.href='/login_admin'</script>"
    else:
        payload = {
            'nama': cari['nama'],
            'username': cari['username'],
            'level': cari['level']
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        session["token"] = token
        session["isLogin"] = True
        session["user"] = {
            "name": cari['nama'],
            "username": cari['username'],
            "level": cari['level'],
            "fotoProfil": cari['fotoProfil'],
            "fotoSampul": cari['fotoSampul'],
        }
        return redirect(url_for("home_admin"))


@app.route("/home_admin")
def home_admin():
    if not session.get("token"):
        return redirect(url_for("login_admin"))

    try:
        token = session["token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return redirect(url_for("login_admin"))

    pending_users = db.user.find({'status': {'$in': ['pending', 'verified']}})

    return render_template('validasi_akun_admin.html', pending_users=pending_users, nama=payload["nama"], username=payload["username"], level=payload["level"], session=session)


@app.route('/home_admin/verify/<username>')
def verify_user(username):
    db.user.update_one({'username': username}, {
                       '$set': {'status': 'verified'}})
    return redirect('/home_admin')


@app.route('/data_warga', methods=['POST'])
def data_warga():
    if request.method == 'POST':
        noKK = request.form['noKK']
        namaLengkap = request.form['namaLengkap']
        nik = request.form['nik']
        tempatLahir = request.form['tempatLahir']
        tanggalLahir = request.form['tanggalLahir']
        jenisKelamin = request.form['jenisKelamin']
        agama = request.form['agama']
        keterangan = request.form['keterangan']

        db.data_warga.insert_one({
            'noKK': noKK,
            'namaLengkap': namaLengkap,
            'nik': nik,
            'tempatLahir': tempatLahir,
            'tanggalLahir': tanggalLahir,
            'jenisKelamin': jenisKelamin,
            'agama': agama,
            'keterangan': keterangan
        })
        return redirect('/data_warga')

    return render_template('/data_warga.html')


@app.route('/data_warga')
def tampil_data_warga():
    data_warga = list(db.data_warga.find())

    jumlah_perempuan = db.data_warga.count_documents(
        {'jenisKelamin': 'Perempuan'})
    jumlah_laki_laki = db.data_warga.count_documents(
        {'jenisKelamin': 'Laki-Laki'})

    jumlah_warga = db.data_warga.count_documents({})

    return render_template('data_warga.html', data=data_warga, jumlah_perempuan=jumlah_perempuan, jumlah_laki_laki=jumlah_laki_laki, jumlah_warga=jumlah_warga)


@app.route('/delete/<nik>')
def delete(nik):
    db.data_warga.delete_one({'nik': nik})

    return redirect('/data_warga')


@app.route("/user")
def user():
    data_sosial = db.social.find({"user": session["user"]["username"] if "user" in session else ""})
    return render_template("profile.html", session=session , data_sosial = data_sosial)


@app.route('/user/<username>', methods=['GET'])
def username(username):
    token_receive = request.cookies.get(TOKEN_KEY)
    try:

        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        status = username == payload.get('id')
        user_info = db.user.find_one(
            {'username': username},
            {'_id': False}
        )
        return render_template(
            'profile.html',
            user_info=user_info,
            status=status
        )
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('home'))


@app.route("/update_profile", methods=["POST"])
def save_img():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        name_receive = request.form["name_give"]
        email_receive = request.form["email_give"]

        new_doc = {"profile_name": name_receive, "profile_info": email_receive}

        if "file_give" in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]

            file_path = f"profile_bg/{username}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_bg"] = filename
            new_doc["profile_bg_real"] = file_path

        if "file_give2" in request.files:
            file = request.files["file_give2"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]

            file_path = f"profile_pf/{username}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pf"] = filename
            new_doc["profile_pf_real"] = file_path

        db.user.update_one({"username": payload["id"]}, {"$set": new_doc})
        return jsonify({"result": "success", "msg": "Profile updated!"})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/pengajuan_surat', methods=['POST'])
def pengajuan_surat():
    if request.method == 'POST':
        jenisSurat = request.form['jenisSurat']
        namaLengkap = request.form['namaLengkap']
        ttl = request.form['ttl']
        jenisKelamin = request.form['jenisKelamin']
        alamat = request.form['alamat']
        agama = request.form['agama']
        nohp = request.form['nohp']

        db.pengajuan_surat.insert_one({
            'jenisSurat': jenisSurat,
            'namaLengkap': namaLengkap,
            'ttl': ttl,
            'jenisKelamin': jenisKelamin,
            'alamat': alamat,
            'agama': agama,
            'nohp': nohp,
            'status': 'Pending',
            'fileSurat': ''
        })
        return redirect('/pengajuan_surat')

    return render_template('/pengajuan_surat_user.html')


@app.route('/pengajuan_surat')
def pengajuan_surat_cetak():
    pengajuan_surat = db.pengajuan_surat.find()
    return render_template('pengajuan_surat_user.html', surat=pengajuan_surat)


@app.route('/validasi_surat')
def validasi_surat():
    if not session.get("token"):
        return redirect(url_for("login_admin"))

    try:
        token = session["token"]
        print(session)
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return redirect(url_for("login_admin"))

    pengajuan_surat = db.pengajuan_surat.find(
        {'status': {'$in': ['Pending', 'Selesai']}})
    return render_template('validasi_surat_admin.html', session=session, pengajuan_surat=pengajuan_surat, nama=payload["nama"], username=payload["username"], level=payload["level"])


@app.route("/validasi_surat/verify/<nohp>", methods=['POST'])
def verify_surat(nohp):
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    fileSurat = request.files['fileSurat']
    extension = fileSurat.filename.split('.')[-1]
    fileSurat_name = f'static/file/fileSurat-{mytime}.{extension}'
    fileSurat.save(fileSurat_name)

    db.pengajuan_surat.update_one(
        {'nohp': nohp}, {'$set': {'fileSurat': fileSurat_name, 'status': 'Selesai'}})
    
    return redirect(url_for("validasi_surat"))


@app.route("/download/<fileSurat_name>", methods=['GET'])
def download_file(fileSurat_name):
    path = os.path.dirname(os.path.abspath(__file__))
    filename = path+"/static/file/"+fileSurat_name
    print(path)
    if filename:
        return send_file(filename, as_attachment=True)
    else:
        return "File not found."

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/pengumuman", methods=['POST'])
def pengumuman_insert():
    tentang= request.form['tentang']
    foto= request.files['foto']
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    extension = foto.filename.split('.')[-1]
    foto_name = f'static/foto_pengumuman/foto-{mytime}.{extension}'
    foto.save(foto_name)

    isipengumuman= request.form['isipengumuman']
    current_date = today.strftime('%A, %d %B %Y')
    id_pengumuman = str(datetime.now())
    namalengkap = session["user"]["name"]
    

    db.pengumuman.insert_one({
        'namauser' : namalengkap,
        'tentang' : tentang,
        'foto' : foto_name,
        'fotoprofil' : session['user']['fotoProfil'],
        'isipengumuman' : isipengumuman,
        'tanggal':current_date,
        'love': 0,
        'like': 0,
        'id_pengumuman' : id_pengumuman,
    })
    return redirect(url_for("pengumuman_GET"))

@app.route("/pengumuman")
def pengumuman_GET():
    datas = db.pengumuman.find({})
    jadwals = db.jadwalronda.find({})
    return render_template('pengumuman_admin.html', datas=datas, jadwal=jadwals)


@app.route('/delete_pengumuman/<id_pengumuman>')
def delete_pengumuman(id_pengumuman):
    db.pengumuman.delete_one({'id_pengumuman': id_pengumuman})
    return redirect("/pengumuman")

@app.route('/pengumuman_edit', methods=['POST'])
def pengumuman_edit():
    tentang= request.form['tentang']
    foto= request.files['foto']
    isipengumuman= request.form['isipengumuman']
    id_pengumuman = request.form['id_pengumuman']
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    current_date = today.strftime('%A, %d %B %Y')

    query = {"id_pengumuman": id_pengumuman}
    if foto:
        extension = foto.filename.split('.')[-1]
        foto_name = f'static/foto_pengumuman/foto-{mytime}.{extension}'
        foto.save(foto_name)
        newData = {"$set": {
            'tentang' : tentang,
            'foto' : foto_name,
            'isipengumuman' : isipengumuman,
            'tanggal':current_date,
        }}
    else:
        newData = {"$set": {
            'tentang' : tentang,
            'isipengumuman' : isipengumuman,
            'tanggal':current_date,
        }}
    ubah = db.pengumuman.update_one(query, newData)
    return redirect("/pengumuman")

@app.route("/pengumuman_love", methods=["POST"])
def pengumuman_love():
    id_pengumuman = request.form["id"]
    query = {"id_pengumuman": id_pengumuman}

    data_pengumuman = db.pengumuman.find_one(query)
    data_pengumuman["love"] += 1
    newValue = {"$set": data_pengumuman}

    update = db.pengumuman.update_one(query, newValue)
    return str(data_pengumuman["love"])

@app.route("/pengumuman_like", methods=["POST"])
def pengumuman_like():
    id_pengumuman = request.form["id"]
    query = {"id_pengumuman": id_pengumuman}

    data_pengumuman = db.pengumuman.find_one(query)
    data_pengumuman["like"] += 1
    newValue = {"$set": data_pengumuman}

    update = db.pengumuman.update_one(query, newValue)
    return str(data_pengumuman["like"])



@app.route("/jadwalronda", methods=['POST'])
def jadwalronda():
    tanggal= request.form['tanggal']
    nama1 = request.form['nama1']
    nama2 = request.form['nama2']
    nama3 = request.form['nama3']
    nama4 = request.form['nama4']
    id_jadwalronda = str(datetime.now())
  
    db.jadwalronda.insert_one({
        'id_jadwalronda' : id_jadwalronda,
       'tanggal' : tanggal,
        'nama1' : nama1,
        'nama2' : nama2,
        'nama3' : nama3,
        'nama4' : nama4,
      
    })
    return redirect("/pengumuman")

@app.route("/pengumuman")
def jadwalGET():
    jadwals = db.jadwalronda.find({})
    return render_template('pengumuman_admin.html', jadwal=jadwals)

@app.route('/delete_jadwalronda/<id_jadwalronda>')
def delete_jadwalronda(id_jadwalronda):
    db.jadwalronda.delete_one({'id_jadwalronda': id_jadwalronda})
    return redirect("/pengumuman")

@app.route('/jadwalronda_edit', methods=['POST'])
def jadwalronda_edit():
    tanggal= request.form['tanggal']
    nama1 = request.form['nama1']
    nama2 = request.form['nama2']
    nama3 = request.form['nama3']
    nama4 = request.form['nama4']
    id_jadwalronda = request.form['id_jadwalronda']
    query = {"id_jadwalronda": id_jadwalronda}

    newData = {"$set": {
        'tanggal' :tanggal ,
        'nama1' : nama1,
        'nama2':nama2,
        'nama3' : nama3,
        'nama4' : nama4,
    }}
    ubah = db.jadwalronda.update_one(query, newData)
    return redirect("/pengumuman")





@app.route("/sosial")
def sosial():
    data_sosial = db.social.find()
    return render_template("sosial.html", data_sosial=data_sosial, session = session)


@app.route("/sosial", methods=["POST"])
def social_insert():
    user = session["user"]["username"]
    isi = request.form["isi_post"]
    foto_profil = session['user']['fotoProfil'],
    

    db.social.insert_one({"user": user, "isi": isi, "love": 0, "like": 0, "foto_profil" : foto_profil[0]})
    return redirect(url_for("sosial"))


@app.route("/sosial_edit", methods=["POST"])
def social_edit():
    id_post = request.form["id"]
    isi_post = request.form["isi_post"]

    query = {"_id": ObjectId(id_post)}
    newData = {"$set": {"isi": isi_post}}
    ubah = db.social.update_one(query, newData)

    if ubah.modified_count > 0:
        script = "<script>alert('Berhasil mengedit data sosial'); location.href='sosial'</script>"
    else:
        script = "<script>alert('Tidak ada data yang diedit'); location.href='sosial'</script>"

    return script

@app.route("/medsos", methods=["POST"])
def social_user():
    user = session["user"]["username"]
    isi = request.form["isi_post"]

    db.social.insert_one({"user": user, "isi": isi, "love": 0, "like": 0})
    return redirect(url_for("user"))


@app.route("/sosial_delete", methods=["GET"])
def social_delete():
    id = request.args.get("id")
    redirect_location = request.args.get("redirect") or 'sosial'
    hapus = db.social.delete_one({"_id": ObjectId(id)})
    print(hapus.deleted_count)

    if hapus.deleted_count > 0:
        script = "<script>alert('Berhasil menghapus data sosial'); location.href='" + redirect_location + "'</script>"
    else:
        script = "<script>alert('Tidak ada data yang dihapus'); location.href='" + redirect_location + "'</script>"
    return script


@app.route("/sosial_love", methods=["POST"])
def social_love():
    id_post = request.form["id"]
    query = {"_id": ObjectId(id_post)}

    data_post = db.social.find_one(query)
    data_post["love"] += 1
    newValue = {"$set": data_post}

    update = db.social.update_one(query, newValue)
    return str(data_post["love"])

@app.route("/sosial_like", methods=["POST"])
def social_like():
    id_post = request.form["id"]
    query = {"_id": ObjectId(id_post)}

    data_post = db.social.find_one(query)
    data_post["like"] += 1
    newValue = {"$set": data_post}

    update = db.social.update_one(query, newValue)
    return str(data_post["like"])

@app.route("/edit_profile", methods=["POST"])
def edit_profile():
    nama= request.form['edit_nama']
    edit_sampul= request.files['edit_bg']
    edit_fotoprofil = request.files['edit_foto']
    edit_email = request.form['edit_email']

    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    # # Upload foto profil
    extension = edit_fotoprofil.filename.split('.')[-1]
    edit_fotoprofil_name = f'static/foto_user/foto_profile-{mytime}.{extension}'
    edit_fotoprofil.save(edit_fotoprofil_name)

    # # Upload foto sampul
    extension = edit_sampul.filename.split('.')[-1]
    edit_sampul_name = f'static/foto_user/foto_sampul-{mytime}.{extension}'
    edit_sampul.save(edit_sampul_name)

    data_username = session["user"]["username"]
    data_user = session["user"]
    data_user["fotoProfil"] = edit_fotoprofil_name
    data_user["fotoSampul"] = edit_sampul_name
    session["user"] = data_user

    query = {"username": data_username}
    newData = {"$set": {
        'nama': nama,
        'fotoSampul': edit_sampul_name,
        'fotoProfil': edit_fotoprofil_name,
        'email': edit_email
    }}

    

    ubah = db.user.update_one(query, newData)
    return redirect(url_for("user"))


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
