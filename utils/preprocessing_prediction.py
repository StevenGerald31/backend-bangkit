import os
from pandas import concat
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from flask import jsonify
from app.db_connection import create_db_connection  # Adjust based on your project structure


def data_inflasi(id_daerah):
    """
    Fungsi untuk mengambil semua data inflasi untuk wilayah tertentu (id_daerah) dari database
    dan mengembalikannya dalam bentuk DataFrame.

    :param id_daerah: ID wilayah untuk mengambil data inflasi.
    :return: DataFrame yang berisi data inflasi atau error message jika gagal.
    """
    # Membuat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return {"error": "Database connection failed"}

    try:
        # Query untuk mengambil data inflasi berdasarkan id_daerah
        query = """
            SELECT tingkat_inflasi, tanggal_inflasi
            FROM inflasi
            WHERE id_daerah = %s
            ORDER BY tanggal_inflasi ASC
        """
        cursor = connection.cursor()
        cursor.execute(query, (id_daerah,))
        data = cursor.fetchall()

        # Menutup koneksi database
        connection.close()

        # Cek jika data tidak ditemukan
        if not data:
            return {"message": f"No data found for id_daerah: {id_daerah}"}

        # Mengonversi data ke DataFrame
        df = pd.DataFrame(data, columns=["tingkat_inflasi", "tanggal_inflasi"])

        # Menghilangkan kolom tanggal_inflasi
        df = df.drop(columns=["tanggal_inflasi"])

        # Mengembalikan DataFrame
        return df

    except Exception as e:
        # Menangani kesalahan
        return {"error": str(e)}
    

def data_komoditas(daerah_id):
    """
    Fungsi untuk mengambil semua data harga komoditas untuk wilayah tertentu (daerah_id) dari database
    dan mengembalikannya dalam bentuk DataFrame.

    :param daerah_id: ID wilayah untuk mengambil data harga komoditas.
    :return: DataFrame yang berisi data harga komoditas atau error message jika gagal.
    """
    # Membuat koneksi ke database
    connection = create_db_connection()
    if not connection:
        return {"error": "Database connection failed"}

    try:
        # Query untuk mengambil data harga komoditas berdasarkan daerah_id
        query = "SELECT * FROM harga_komoditas WHERE daerah_id = %s"
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (daerah_id,))
        
        data_harga_komoditas = {
        "prices": cursor.fetchall(),
        }
        connection.close()

        if not data_harga_komoditas['prices']:
            return jsonify({"message": "Data not found for daerah_id: {}".format(daerah_id)}), 404

        # Process the data to create a DataFrame with commodity columns
        prices = data_harga_komoditas['prices']
        
        # Create a dictionary to store data for each commodity
        commodities_data = {}

        # Loop through each price entry to organize data by commodity
        for price_data in prices:
            date = price_data['tanggal_harga']
            komoditas_id = price_data['komoditas_id']
            harga = price_data['harga']

            # Initialize the commodity list if it doesn't exist
            if komoditas_id not in commodities_data:
                commodities_data[komoditas_id] = []

            # Append the price data for the given date
            commodities_data[komoditas_id].append({"tanggal_harga": date, "harga": harga})

        # Convert the commodity data into a DataFrame
        df_data = []
        dates = sorted(set([entry['tanggal_harga'] for entry in prices]))  # Collect unique dates

        # Fill in the data for each commodity and date
        for date in dates:
            row = {"tanggal_harga": date}
            for komoditas_id in range(1, 6):  # Adjust range based on the number of commodities you have
                filtered_prices = [entry['harga'] for entry in commodities_data.get(komoditas_id, []) if entry['tanggal_harga'] == date]
                row[f'komoditas_id_{komoditas_id}'] = filtered_prices[0] if filtered_prices else None
            df_data.append(row)

        # Create a DataFrame from the collected data
        df = pd.DataFrame(df_data)


        # Mengembalikan DataFrame
        return df

    except Exception as e:
        # Menangani kesalahan
        return {"error": str(e)}

def data_inflasi_dan_komoditas(id_daerah):
    """
    Fungsi untuk mengambil data inflasi dan harga komoditas untuk wilayah tertentu (id_daerah),
    kemudian menggabungkan keduanya dalam satu DataFrame.

    :param id_daerah: ID wilayah untuk mengambil data inflasi dan harga komoditas.
    :return: DataFrame yang berisi gabungan data inflasi dan harga komoditas.
    """
    # Ambil data inflasi
    inflasi_df = data_inflasi(id_daerah)
    if isinstance(inflasi_df, dict) and "error" in inflasi_df:
        return inflasi_df  # Jika gagal mengambil data inflasi

    # Ambil data harga komoditas
    komoditas_df = data_komoditas(id_daerah)
    if isinstance(komoditas_df, dict) and "error" in komoditas_df:
        return komoditas_df  # Jika gagal mengambil data harga komoditas

    try:
        # Drop the tanggal_harga column from komoditas_df
        komoditas_df = komoditas_df.drop(columns=['tanggal_harga'])
        # Gabungkan kedua DataFrame berdasarkan indeks
        merged_df = pd.concat([komoditas_df, inflasi_df], axis=1)

        # Mengembalikan DataFrame hasil penggabungan
        return merged_df

    except Exception as e:
        # Tangani kesalahan jika terjadi
        return {"error": str(e)}
    

def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    n_vars = 1 if type(data) is list else data.shape[1]
    df = pd.DataFrame(data)
    cols, names = list(), list()
    
    # Input sequence
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
    
    # Forecast sequence
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' %  (j+1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j+1, i)) for j in range(n_vars)]
    
    # Concatenate all columns
    agg = concat(cols, axis=1)
    agg.columns = names
    
    if dropnan:
        agg.dropna(inplace=True)
    
    return agg


