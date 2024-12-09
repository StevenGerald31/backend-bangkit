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

@routes.route('/harga_komoditas/<int:daerah_id>', methods=['GET'])
def get_time_series_by_region(daerah_id):
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)
    query = "SELECT * FROM harga_komoditas WHERE daerah_id = %s"  # Pastikan nama kolom sesuai dengan tabel Anda
    cursor.execute(query, (daerah_id,))
    result = {
            "error": False,
            "message": "Success",
            "prices":cursor.fetchall(),
            "description": "Harga normal hasil dari aplikasi HP filter pada harga komoditas di daerah tertentu"
        }
    connection.close()

    if not result:
        return jsonify({"message": "Data not found for daerah_id: {}".format(daerah_id)}), 404

    return jsonify(result)

@routes.route('/harga_komoditas/<int:daerah_id>/<int:komoditas_id>', methods=['GET'])
def get_time_series_by_region_and_commodity(daerah_id, komoditas_id):
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT * FROM harga_komoditas 
        WHERE daerah_id = %s AND komoditas_id = %s
    """  # Pastikan nama kolom sesuai dengan tabel Anda
    cursor.execute(query, (daerah_id, komoditas_id))
    result = {
            "error": False,
            "message": "Success",
            "prices":cursor.fetchall(),
            "description": "Harga normal hasil dari aplikasi HP filter pada harga komoditas di daerah tertentu"
        }
    connection.close()

    if not result:
        return jsonify({
            "message": "Data not found for daerah_id: {} and komoditas_id: {}".format(daerah_id, komoditas_id)
        }), 404

    return jsonify(result)

@routes.route('/harga_normal/<int:daerah_id>/<int:komoditas_id>', methods=['GET'])
def get_harga_normal(daerah_id, komoditas_id):
    # Buat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Query data harga berdasarkan daerah_id dan komoditas_id
        query = """
            SELECT tanggal_harga, harga 
            FROM harga_komoditas 
            WHERE daerah_id = %s AND komoditas_id = %s
            ORDER BY tanggal_harga
        """
        cursor = connection.cursor()
        cursor.execute(query, (daerah_id, komoditas_id))
        data = cursor.fetchall()

        # Tutup koneksi database
        connection.close()

        # Cek apakah data tersedia
        if not data:
            return jsonify({"message": f"No data found for daerah_id: {daerah_id} and komoditas_id: {komoditas_id}"}), 404

        # Konversi hasil query menjadi DataFrame
        df = pd.DataFrame(data, columns=['tanggal_harga', 'Harga'])

        # Terapkan HP Filter
        cycle, trend = hpfilter(df['Harga'], lamb=24414062500)
        df['Harga_Normal'] = trend.astype(int)  # Tambahkan kolom harga normal

        # Konversi hasil ke JSON
        result = {
            "error": False,
            "message": "Success",
            "prices": df[['tanggal_harga', 'Harga_Normal']].to_dict(orient='records'),
            "description": "Harga normal hasil dari aplikasi HP filter pada harga komoditas di daerah tertentu"
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
                "tingkat_inflasi": data[0],
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
        query = "SELECT daerah_id, nama_daerah FROM daerah"
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
                "nama_daerah": row[1]
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


from keras.src.legacy.saving import legacy_h5_format
model = legacy_h5_format.load_model_from_hdf5("model/model_jakarta_pusat.h5", custom_objects={'mse': 'mse'})

@routes.route('/inflasiall/<int:id_daerah>', methods=['GET'])
def get_all_inflasi(id_daerah):
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
        """
        cursor = connection.cursor()
        cursor.execute(query, (id_daerah,))
        data = cursor.fetchall()

        # Tutup koneksi database
        connection.close()

        # Cek apakah data tersedia
        if not data:
            return jsonify({"message": f"No data found for id_daerah: {id_daerah}"}), 404

        # Membuat DataFrame dari hasil query
        df_inflasi = pd.DataFrame(data, columns=['tingkat_inflasi', 'tanggal_inflasi'])

        # Kembalikan hasil query dalam format JSON
        return jsonify({
            "error": False,
            "message": "Success",
            "data": df_inflasi.to_dict(orient='records')  # Konversi DataFrame ke list of dicts
        })
    except Exception as e:
        # Handle error
        return jsonify({"error": str(e)}), 500
    
# Fungsi untuk mengambil data harga komoditas dari database
def get_data_model(daerah_id, komoditas_id):
    connection = create_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        query = f"""
        SELECT tanggal_harga, komoditas_id, harga
        FROM harga_komoditas
        WHERE daerah_id = %s AND komoditas_id IN ({','.join(['%s'] * len(komoditas_id))})
        ORDER BY tanggal_harga ASC
        """
        cursor = connection.cursor()
        cursor.execute(query, [daerah_id] + komoditas_id)
        result = cursor.fetchall()
        connection.close()

        data = pd.DataFrame(result, columns=['tanggal_harga', 'komoditas_id', 'harga'])
        return data
    
    except Exception as e:
        if connection.is_connected():
            connection.close()
        return jsonify({"error": str(e)}), 500




# Fungsi untuk prediksi inflasi
@routes.route('/predict', methods=['GET'])
def predict_inflation():
    daerah_id = request.args.get('daerah_id', type=int, default=1)
    komoditas_ids = [1, 2, 3, 4, 5]  # Termasuk daging ayam (id_komoditas = 5)

    # Ambil data harga komoditas dari database
    data = get_data_model(daerah_id, komoditas_ids)
    
    if data.empty:
        return jsonify({"error": "No commodity price data found for the region"}), 404

    # Ambil data tingkat inflasi dari database
    # Panggil fungsi get_all_inflasi untuk mendapatkan data inflasi
    inflasi_response = get_all_inflasi(daerah_id)
    
    # Ambil data JSON dari response
    inflasi_data = inflasi_response.get_json()  # Mengambil data JSON dari response

    if "data" not in inflasi_data or not inflasi_data["data"]:
        return jsonify({"error": f"No inflation data found for the region with daerah_id {daerah_id}"}), 404

    # Konversi data inflasi ke DataFrame
    inflasi_df = pd.DataFrame(inflasi_data["data"])

    # Gabungkan data harga komoditas dengan data inflasi berdasarkan tanggal_harga
    data = data.merge(inflasi_df[['tanggal_inflasi', 'tingkat_inflasi']], left_on='tanggal_harga', right_on='tanggal_inflasi', how='left')

    # Pivot data untuk membuat format yang sesuai
    data_pivot = data.pivot(index='tanggal_harga', columns='komoditas_id', values='harga')
    data_pivot.columns = ['Bawang Merah', 'Bawang Putih', 'Cabai Merah Keriting', 'Cabai Rawit Hijau', 'Daging Ayam']

    # Tambahkan kolom tingkat inflasi sebagai fitur ke data pivot
    data_pivot['Tingkat Inflasi'] = data['tingkat_inflasi']
    
    # Normalisasi data
    scaler_features = MinMaxScaler(feature_range=(0, 1))
    scaled_features = scaler_features.fit_transform(data_pivot)

    # Ambil data terakhir untuk prediksi
    input_seq = scaled_features[-1].reshape(1, 1, scaled_features.shape[1])  # Data terakhir

    # Prediksi dengan model
    pred = model.predict(input_seq)

    # Denormalisasi hasil prediksi
    scaler_target = MinMaxScaler(feature_range=(0, 1))  # Anda perlu scaler yang sama saat melatih
    predicted_inflation = scaler_target.inverse_transform(pred.reshape(-1, 1))

    # Return hasil prediksi
    return jsonify({
        'predicted_inflation': float(predicted_inflation.flatten()[0])
    })