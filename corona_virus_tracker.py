import time
import json
import sys
import datetime
import numpy as np
import pandas as pd
from os import remove
import urllib.request
from csv import writer, reader
from bokeh.palettes import Turbo256
from bokeh.transform import linear_cmap
from bokeh.plotting import figure, ColumnDataSource
from bokeh.tile_providers import get_provider, Vendors
from bokeh.io import output_notebook, show, output_file
from bokeh.models import ColorBar, NumeralTickFormatter, Title


KEEP_RUNNING = True
RUN_ONCE = True
WAIT = 1800 # sec ie 0.5 hours
TOTAL_DURATION = WAIT
row_contents = []

print('Fetching data...')

while KEEP_RUNNING:
    # using api to fetch the data.
    url = 'https://api.apify.com/v2/key-value-stores/toDWvRj1JpTXiM8FF/records/LATEST?disableRedirect=true'
    response = urllib.request.urlopen(url).read()
    json_obj = str(response, 'utf-8')
    # loading api's json output to data
    data = json.loads(json_obj)
    
    # removing virus_stat_csv to store new data
    try:
        remove(r'csv_files/virus_stats.csv')
    except FileNotFoundError:
        pass
    
    # storing json data into a file
    with open(r'json/data_file.json', 'w') as write_file:
        json.dump(data, write_file)

    # opening latitude and longitude coordinates csv file and store the data in the list format
    with open(r'csv_files/coordinates.csv', newline='') as coordinate_csv:
        csv_reader = reader(coordinate_csv)
        data1 = list(csv_reader)

    # this function stores the fetched data in list format into virus_stat.csv file
    def append_list_as_row(file_name, list_of_elem):
        with open(file_name, 'a+', newline='') as write_obj:
            csv_writer = writer(write_obj)
            csv_writer.writerow(list_of_elem)

    # this addes the header to the virus_stat.csv file
    row_header = ['region', 'totalInfected', 'newInfected','recovered', 'newRecovered', 'deceased', 'newDeceased', 'latitude', 'longitude']
    append_list_as_row(r'csv_files/virus_stats.csv', row_header)

    # clear list content
    row_contents.clear()
    # row = 1 denotes first row of coordinate.csv
    row = 1 
    # latitude = 1 denotes the column 1 of coordinate.csv
    latitude = 1
    # longitude = 2 denotes the column 2 of coordinate.csv
    longitude = 2


    # using for loop we are fetching json data and storing the data as list in row_contents. 
    # and calling append_list_as_row() function to store data for region, totalCases, totalInfected, 
    # recovered, deceased, latitude and longitude
    for item in data['regionData']:
        row_contents.append(item['region'])
        row_contents.append(item['totalInfected'])
        row_contents.append(item['newInfected'])
        row_contents.append(item['recovered'])
        row_contents.append(item['newRecovered'])
        row_contents.append(item['deceased'])
        row_contents.append(item['newDeceased'])
        row_contents.append(data1[row][latitude])
        row_contents.append(data1[row][longitude])
        row += 1
        append_list_as_row(r'csv_files/virus_stats.csv', row_contents)
        row_contents.clear()

    # opening virus_stat.csv file and deleting last 2 rows of unnecessary data
    # because last 2 rows of data doesnot contain any corona virus stats related to 'states' 
    # in india
    with open(r'csv_files/virus_stats.csv', 'r+') as virus_stat_csv:
        lines = virus_stat_csv.readlines()
        lines.pop()
        lines.pop()

    # after deleting the last 2 rows, save the changes using write options
    with open(r'csv_files/virus_stats.csv', 'w+') as virus_stat_csv:
        virus_stat_csv.writelines(lines)
        virus_stat_csv.close()

    # using pandas read the virus_stat.csv and store it to df(data frames)
    df = pd.read_csv(r'csv_files/virus_stats.csv')

    # This function takes the latitude & latitude coordinates and converts into mercator format.
    # because bokeh module uses mercator coordinates instead of latitude and longitude for mapping
    # this function returns tuples
    def x_coord(x, y):
        lat = x
        lon = y

        r_major = 6378137.000
        x = r_major * np.radians(lon)
        scale = x / lon
        y = 180.0 / np.pi * np.log(np.tan(np.pi / 4.0 +
                                          lat * (np.pi / 180.0) / 2.0)) * scale
        return (x, y)


    # zip() makes latitude and logitude coordinate into tuple form, and using list()
    # we are storing storing tuples into list ex: [(), (), (),...]
    df['coordinates'] = list(zip(df['latitude'], df['longitude']))
    #meracators stores the coverted lat and long values using list comprehension in tuple formate
    # ex: [(), (),(),...]
    mercators = [x_coord(x, y) for x, y in df['coordinates']]

    # meracator is a column which stores the meracators values in tuple format
    df['mercator'] = mercators
    # using series we are splitting tuple into 2 separete column
    df[['mercator_x', 'mercator_y']] = df['mercator'].apply(pd.Series)

    # helps to select map type, STAMEN_TONER gives black and white map
    chosentile = get_provider(Vendors.STAMEN_TONER)

    # pallet color ie color bar graph
    palette = Turbo256

    # source store the data as source of data
    source = ColumnDataSource(data=df)

    # bar graph for min to max cases
    color_mapper = linear_cmap(field_name='totalInfected', palette=palette, low=df['totalInfected'].min(),
                               high=df['totalInfected'].max())

    # tool tips which displays below values when we click on it
    tooltips = [('Region', '@region'), ('Total Infected', '@totalInfected'), ('New Infected', '@newInfected'),
                ('Total Recovered', '@recovered'), ('New Recovered', '@newRecovered'), ('Total Deceased', '@deceased'), ('New Deceased', '@newDeceased')]

    # figure contains details for map sizes
    plot = figure(plot_width=850, plot_height=850, x_axis_type='mercator', y_axis_type='mercator',
                  x_axis_label='Longitude', y_axis_label='Latitude', tooltips=tooltips)

    # this will add map tile
    plot.add_tile(chosentile)

    # this adds circular regions on the map
    plot.circle(x='mercator_x', y='mercator_y', color=color_mapper, source=source, size=30, fill_alpha=0.7)

    # this gives the information of the bar on the right
    color_bar = ColorBar(color_mapper=color_mapper['transform'],
                         formatter=NumeralTickFormatter(format='00'),
                         label_standoff=13, width=8, location=(0, 0))

    title = 'Total Cases: ' + str(data['totalCases']) + ', Active Cases: ' + str(data['activeCases']) \
            + ', Recovered: ' + str(data['recovered']) + ', Deceased: ' + str(data['deaths'])

    # this puts the bar on the right
    plot.add_layout(color_bar, 'right')
    # this puts the title at the top in center
    plot.add_layout(Title(text=title, align='center'), 'above')
    # this puts the title at the top in center
    plot.add_layout(Title(text='Corona virus cases in India', align='center', text_font_size='15px'), 'above')
    # this puts the title at the bottom in centre
    plot.add_layout(Title(text='https://www.mohfw.gov.in/', align='center', text_font_size='10px'), 'below')

    # his creates the html file named corona_tracker.html
    output_file('corona_tracker.html', title='Corona cases in India')

    # using if statement once so that web-page popups only once
    if RUN_ONCE:
        show(plot)
        RUN_ONCE = False

    print('\nUpdating data...')

    # this for loop is used to display the progress bar like |█████████████████----------|
    for sec in range(WAIT):
        filled_length = int(100 * (sec + 1) // WAIT)
        bar = '█' * filled_length + '-' * (100 - filled_length)
        sys.stdout.write('\r{0} |{1}| {2} '.format(datetime.timedelta(seconds=sec + 1),
                                                   bar, datetime.timedelta(seconds=TOTAL_DURATION)))
        # usinf flush we are deleting and updating the new bar at the same place
        sys.stdout.flush()
        time.sleep(1)

        # sec reaches max wait time then it will print below statement
        if sec + 1 == WAIT:
            print('\nRefresh web-page manually to get the latest update')

    # closing opened file
    write_file.close()
    coordinate_csv.close

