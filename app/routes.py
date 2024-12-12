from flask import Blueprint, jsonify, request
from .db_connection import create_db_connection
import numpy as np
from tensorflow.keras.models import load_model
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.filters.hp_filter import hpfilter
import requests
from io import BytesIO
import pandas as pd
import pickle
from tensorflow.keras.models import load_model
from tensorflow.keras import metrics
from datetime import datetime, timedelta, date
from utils.preprocessing_prediction import data_inflasi_dan_komoditas, series_to_supervised


routes = Blueprint('routes', __name__)

@routes.route('/harga_komoditas', methods=['GET'])
def get_time_series():
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)
    query = "SELECT * FROM harga_komoditas"  # Ganti dengan nama tabel Anda
    cursor.execute(query)
    result = cursor.fetchall()
    connection.close()
    return jsonify(result)



@routes.route('/harga_komoditas/<int:daerah_id>/<int:komoditas_id>', methods=['GET'])
def get_time_series_by_region_and_commodity(daerah_id, komoditas_id):
    # Baca parameter `timeRange` dari query string
    time_range = request.args.get('timeRange', default=1, type=int)  # Default 1 tahun jika tidak ada parameter

    # Buat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Hitung tanggal awal berdasarkan timeRange
        start_date = datetime.now() - timedelta(days=time_range * 365)
        start_date_str = start_date.strftime('%Y-%m-%d')

        # Query untuk mengambil data dengan filter timeRange
        query = """
            SELECT * 
            FROM harga_komoditas
            WHERE daerah_id = %s AND komoditas_id = %s AND tanggal_harga >= %s
            ORDER BY tanggal_harga ASC
        """  # Pastikan nama kolom sesuai dengan tabel Anda
        cursor.execute(query, (daerah_id, komoditas_id, start_date_str))

        # Ambil hasil query
        prices = cursor.fetchall()

        # Jika tidak ada data
        if not prices:
            return jsonify({
                "error": True,
                "message": "Data not found for daerah_id: {} and komoditas_id: {} in the last {} year(s)".format(
                    daerah_id, komoditas_id, time_range
                )
            }), 404
        
        
        # Format tanggal menjadi dd-mm-yyyy
        for price in prices:
            tanggal_harga = price['tanggal_harga']
            
            # If tanggal_harga is already a datetime object, format it directly
            if isinstance(tanggal_harga, date):
                price['tanggal_harga'] = tanggal_harga.strftime('%d-%m-%Y')
            

        # Format hasil
        result = {
            "error": False,
            "message": "Success",
            "prices": prices,
            "description": "Data harga komoditas dalam {} tahun terakhir untuk daerah {} dan komoditas {}.".format(
                time_range, daerah_id, komoditas_id
            )
        }

        # Tutup koneksi
        connection.close()

        return jsonify(result)
    except Exception as e:
        # Tutup koneksi jika terjadi error
        connection.close()
        return jsonify({"error": str(e)}), 500
    
@routes.route('/harga_komoditas/last/<int:daerah_id>/<int:komoditas_id>', methods=['GET'])
def get_last_price(daerah_id, komoditas_id):
    # Buat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Query untuk mengambil data harga terakhir
        query = """
            SELECT *
            FROM harga_komoditas
            WHERE daerah_id = %s AND komoditas_id = %s
            ORDER BY tanggal_harga DESC
            LIMIT 1
        """  
        cursor.execute(query, (daerah_id, komoditas_id))

        # Ambil hasil query
        last_price = cursor.fetchone()

        # Jika tidak ada data
        if not last_price:
            return jsonify({
                "error": True,
                "message": "No data found for daerah_id: {} and komoditas_id: {}".format(daerah_id, komoditas_id)
            }), 404

        # Format tanggal jika tanggal_harga adalah tipe data date
        if isinstance(last_price['tanggal_harga'], date):
            last_price['tanggal_harga'] = last_price['tanggal_harga'].strftime('%d-%m-%Y')

        # Format hasil
        result = {
            "error": False,
            "message": "Success",
            "last_price": last_price,
            "description": "Data harga komoditas terakhir untuk daerah {} dan komoditas {}.".format(daerah_id, komoditas_id)
        }

        # Tutup koneksi
        connection.close()

        return jsonify(result)

    except Exception as e:
        # Tutup koneksi jika terjadi error
        connection.close()
        return jsonify({"error": str(e)}), 500


@routes.route('/harga_normal/<int:daerah_id>/<int:komoditas_id>', methods=['GET'])
def get_harga_normal_time_range(daerah_id, komoditas_id):
    # Baca parameter `timeRange` dari query string
    time_range = request.args.get('timeRange', default=1, type=int)  # Default 1 tahun jika tidak ada parameter

    # Buat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor()

        # Hitung tanggal awal berdasarkan timeRange
        start_date = datetime.now() - timedelta(days=time_range * 365)
        start_date_str = start_date.strftime('%Y-%m-%d')

        # Query untuk mengambil data dengan filter timeRange
        query = """
            SELECT tanggal_harga, harga
            FROM harga_komoditas
            WHERE daerah_id = %s AND komoditas_id = %s AND tanggal_harga >= %s
            ORDER BY tanggal_harga ASC
        """
        cursor.execute(query, (daerah_id, komoditas_id, start_date_str))

        # Ambil hasil query
        data = cursor.fetchall()

        # Tutup koneksi database
        connection.close()

        # Cek apakah data tersedia
        if not data:
            return jsonify({
                "error": True,
                "message": f"No data found for daerah_id: {daerah_id}, komoditas_id: {komoditas_id}, in the last {time_range} year(s)."
            }), 404

        # Konversi hasil query menjadi DataFrame
        df = pd.DataFrame(data, columns=['tanggal_harga', 'Harga'])

        # Terapkan HP Filter
        cycle, trend = hpfilter(df['Harga'], lamb=24414062500)
        df['Harga_Normal'] = trend.astype(int)  # Tambahkan kolom harga normal

        # Format tanggal jika tanggal_harga adalah tipe data date
        df['tanggal_harga'] = pd.to_datetime(df['tanggal_harga']).dt.strftime('%d-%m-%Y')
        

        # Konversi hasil ke JSON
        result = {
            "error": False,
            "message": "Success",
            "prices": df[['tanggal_harga', 'Harga_Normal']].to_dict(orient='records'),
            "description": f"Harga normal hasil dari aplikasi HP filter dalam {time_range} tahun terakhir untuk komoditas tertentu."
        }

        return jsonify(result)

    except Exception as e:
        # Tangani kesalahan dan tutup koneksi jika belum ditutup
        if connection.is_connected():
            connection.close()
        return jsonify({"error": str(e)}), 500


# get all data komoditas
# Route untuk mengambil semua data dari tabel `komoditas`
@routes.route('/komoditas', methods=['GET'])
def get_all_komoditas():
    # Buat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query untuk mengambil semua data dari tabel komoditas
        query = "SELECT * FROM komoditas"
        cursor = connection.cursor()
        cursor.execute(query)
        data = cursor.fetchall()

        # Tutup koneksi database
        connection.close()

        # Cek apakah data tersedia
        if not data:
            return jsonify({"message": "No data found in komoditas table"}), 404

        # Kembalikan hasil query dalam format JSON
        return jsonify({
            "error": False,
            "message": "Success",
            "data": [{
                "id_komoditas": row[0],
                "nama_komoditas": row[1],
                "img_url": row[2]
            } for row in data]
        })
    except Exception as e:
        # Handle error
        return jsonify({"error": str(e)}), 500

# get all data daerah 


@routes.route('/inflasi/<int:id_daerah>', methods=['GET'])
def get_last_inflasi(id_daerah):
    # Buat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query untuk mengambil data terakhir berdasarkan id_daerah
        query = """
            SELECT tingkat_inflasi, tanggal_inflasi
            FROM inflasi
            WHERE id_daerah = %s
            ORDER BY tanggal_inflasi DESC
            LIMIT 1
        """
        cursor = connection.cursor()
        cursor.execute(query, (id_daerah,))
        data = cursor.fetchone()

        # Tutup koneksi database
        connection.close()

        # Cek apakah data tersedia
        if not data:
            return jsonify({"message": f"No data found for id_daerah: {id_daerah}"}), 404

        # Kembalikan hasil query dalam format JSON
        return jsonify({
            "error": False,
            "message": "Success",
            "data": {
                "tingkat_inflasi": str(data[0]),
                "tanggal_inflasi": data[1]
            }
        })
    except Exception as e:
        # Handle error
        return jsonify({"error": str(e)}), 500
    


@routes.route('/daerah', methods=['GET'])
def get_all_daerah():
    # Buat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query untuk mengambil semua data dari tabel daerah
        query = "SELECT daerah_id, nama_daerah, img_url FROM daerah"
        cursor = connection.cursor()
        cursor.execute(query)
        data = cursor.fetchall()

        # Tutup koneksi database
        connection.close()

        # Cek apakah data tersedia
        if not data:
            return jsonify({"message": "No data found in daerah table"}), 404

        # Format data menjadi list of dictionaries
        formatted_data = [
            {
                "daerah_id": row[0],
                "nama_daerah": row[1],
                "img_url": row[2]
            } for row in data
        ]

        # Kembalikan hasil query dalam format JSON
        return jsonify({
            "error": False,
            "message": "Success",
            "data": formatted_data
        })
    except Exception as e:
        # Handle error
        return jsonify({"error": str(e)}), 500

# code preidksi inflasi
@routes.route('/prediksi/<int:id_daerah>', methods=['GET'])
def prediksi_inflasi_real(id_daerah):
    """
    Endpoint API untuk melakukan prediksi inflasi 1 bulan ke depan berdasarkan id_daerah
    """
    # Mengambil data untuk wilayah yang diminta
    data_prediksi = data_inflasi_dan_komoditas(id_daerah)

    if isinstance(data_prediksi, dict) and "error" in data_prediksi:
        return jsonify(data_prediksi), 400  # Return error if data fetching fails

    try:
        # Menyiapkan fitur dan target
        features = data_prediksi[['komoditas_id_1', 'komoditas_id_2', 'komoditas_id_3', 'komoditas_id_4', 'komoditas_id_5']].values
        target = data_prediksi['tingkat_inflasi'].values.reshape(-1, 1)

        # Normalisasi fitur (harga komoditas)
        scaler_features = MinMaxScaler(feature_range=(0, 1))
        scaled_features = scaler_features.fit_transform(features)

        # Normalisasi target (inflasi)
        scaler_target = MinMaxScaler(feature_range=(0, 1))
        scaled_target = scaler_target.fit_transform(target)

        # Gabungkan kembali fitur dan target yang sudah dinormalisasi
        scaled_data = np.hstack((scaled_features, scaled_target))

        # frame as supervised learning
        reframed = series_to_supervised(scaled_data, 1, 1)
        reframed.drop(reframed.columns[[6, 7, 8, 9, 10]], axis=1, inplace=True)

        # Pisahkan input dan output untuk prediksi
        values = reframed.values
        test_X = values[:, :-1]

        # Ambil data terakhir untuk prediksi 1 bulan ke depan
        input_seq = test_X[-1].reshape(1, 1, test_X.shape[1])  # Ambil data terakhir dan reshape

        # Load the model (ensure model path is correct)
        model = load_model('model.h5')  # Replace with actual model path

        # Prediksi untuk 1 bulan ke depan
        pred = model.predict(input_seq)

        # Denormalisasi hasil prediksi
        predicted_inflation = scaler_target.inverse_transform(pred.reshape(-1, 1))

        # Ambil nilai prediksi pertama (karena hanya satu nilai untuk satu prediksi)
        predicted_inflation_value = predicted_inflation.flatten()[0]

        # Dapatkan data inflasi terakhir dari database
        last_inflation = get_last_inflasi(id_daerah).json.get('data', {}).get('tingkat_inflasi', None)
        if last_inflation is not None:
            last_inflation = float(last_inflation)

        # Interpretasi hasil prediksi
        if last_inflation is not None:
            if predicted_inflation_value > last_inflation:
                deskripsi = ("Inflasi diprediksi akan meningkat dibandingkan bulan sebelumnya, "
                             "yang dapat menunjukkan adanya tekanan pada harga komoditas utama di daerah ini.")
            elif predicted_inflation_value < last_inflation:
                deskripsi = ("Inflasi diprediksi akan menurun dibandingkan bulan sebelumnya, "
                             "menandakan potensi stabilisasi harga komoditas utama di daerah ini.")
            else:
                deskripsi = ("Inflasi diprediksi akan tetap stabil dibandingkan bulan sebelumnya, "
                             "mengindikasikan tidak adanya perubahan signifikan pada harga komoditas utama.")
        else:
            deskripsi = "Data inflasi terakhir tidak tersedia untuk membuat interpretasi."

        # Jika Anda ingin mengembalikan prediksi sebagai response JSON:
        return jsonify({
            "error": False,
            "message": "Success",
            "data": {
                'prediksi_inflasi': str(round(predicted_inflation_value, 2)),
                'deskripsi': deskripsi
            }
        })
    

    except Exception as e:
        # Handle errors
        return jsonify({"error": str(e)}), 500