from flask import Flask, render_template, redirect, render_template_string, request
import pandas as pd
import bokeh
import jinja2
import json
from bokeh.plotting import figure, show
from bokeh.embed import components
import numpy as np
from pandas.io.json import json_normalize
from shapely.geometry.polygon import LinearRing, Polygon
from bokeh.plotting import figure, output_file, show
from bokeh.models import Range1d
from shapely.geometry import Polygon
import seaborn as sns
import matplotlib.pyplot as plt
from address import AddressParser, Address



app = Flask(__name__)

@app.route('/')
def index():
  return render_template('index.html')

# amz converts addresses to the number of floodplains it lies in
def get_count_data():
    with open('/home/amzalucha/mysite/count_dict.json', 'r') as fp:
        count_dict = json.load(fp)
    return count_dict

def make_count_pie(address):
    count_dict=get_count_data()

    count_values=list(count_dict.values())
    labels = ['0 Intersecting Floodplains', '1 Intersecting Floodplain', '2 Intersecting Floodplains', '3 or More Intersecting Floodplains']
    sizes=[count_values.count(i)/len(count_dict.keys()) for i in range(3)]
    sizes.append((count_values.count(3)+count_values.count(4)+count_values.count(5))/len(count_dict.keys()))
    colors = ['yellowgreen', 'aqua', 'blue', 'lightcoral']
    explode_lst=[0, 0, 0, 0]
    explode_lst[count_dict[address]]=0.1
    explode = tuple(explode_lst)
    plt.clf()
    patches, texts = plt.pie(sizes, colors=colors, shadow=True, startangle=90, explode=explode)
    plt.legend(patches, labels, loc="best", fontsize=16)
    plt.axis('equal')
    plt.tight_layout()
    fig = plt.gcf()


    intsect=str(count_dict[address])


    #fig = ax.get_figure()
    fig.set_size_inches(8,8)
    plt.savefig('/home/amzalucha/mysite/static/comparison'+intsect+'.png')
    plt.close(fig)

    #p2=plt.plot(range(10),range(10))
    #plt.savefig('/home/amzalucha/mysite/static/comparison')
    return count_dict[address]

#Make use of address package but it's not an exact match because
#it's written in python 2, so I had to convert *.py files to python 3 using 2to3
def format_address(address_unformatted):
    try:
        addr_no_period_upper=address_unformatted.replace('.', '').replace(',','').upper()
        #The parser gets confused if there isn't a city, state, and zip, so append a dummy one if the user doesn't enter it
        if 'BOULDER' not in addr_no_period_upper:
            addr_no_period_upper=addr_no_period_upper+', BOULDER, CO 80301'
        #It can't seem to parse addresses that have an apartment-like word
        addr_no_apt=addr_no_period_upper.replace('APT', '')
        addr_no_apt=addr_no_apt.replace('UNIT', '')
        addr_no_apt=addr_no_apt.replace('APARTMENT', '')
        addr_no_apt=addr_no_apt.replace('SUITE', '')
        addr_no_apt=addr_no_apt.replace('STE', '')
        addr_no_apt=addr_no_apt.replace('NUMBER', '')
        addr_no_apt=addr_no_apt.replace('NUM', '')
        ap = AddressParser()
        address_parsed = ap.parse_address(addr_no_apt)
        if address_parsed.street_prefix==None:
            address_parsed.street_prefix=''
        if address_parsed.apartment==None:
            address_parsed.apartment=''
        if address_parsed.street_suffix=='Ave.':
            address_parsed.street_suffix='AV'
        address=address_parsed.house_number+' '+address_parsed.street_prefix+' '+address_parsed.street+' '+address_parsed.street_suffix+' '+address_parsed.apartment
        address=address.replace('.', '').replace('  ', ' ').upper()
        if address[-1]==' ':
           address=address[:-1]
        return address
    except:
        return "error"

#converts coordinate list to a list of longitudes and latitudes
def coors_to_lon_lat(coors):
    lon,lat=list(zip(*coors))
    return lon,lat

#converts coordinate list into a polygon object
def coors_to_polygon_creeks(coors):
    lon,lat=coors_to_lon_lat(coors)
    lonlist=list(lon)
    latlist=list(lat)
    lltup=list(zip(lonlist,latlist))
    out=Polygon(lltup)
    return out

def coors_to_polygon_prop(coors):
    if coors[0]=='Polygon':
        lonlats=coors[1][0]
        lon,lat=coors_to_lon_lat(lonlats)
        lonlist=list(lon)
        latlist=list(lat)
        lltup=list(zip(lonlist,latlist))
        out=[Polygon(lltup)]
    else:
        boxlist=[]
        lonlats=coors[1]
        for box in lonlats:
            lon,lat=coors_to_lon_lat(box[0])
            lonlist=list(lon)
            latlist=list(lat)
            lltup=list(zip(lonlist,latlist))
            boxlist.append(Polygon(lltup))
        out=boxlist
    return out

def get_rental_data():
    with open('/home/amzalucha/mysite/prop_dict.json', 'r') as fp:
        prop_dict = json.load(fp)
    return prop_dict

def read_limit_data():
    with open('/home/amzalucha/mysite/boulder_city_limits.json') as json_data:
        data = json.load(json_data)
    df_limits=json_normalize(data["features"])
    limits=[]
    for i in range(len(df_limits['geometry.coordinates'])):
        limits.append(df_limits['geometry.coordinates'][i][0])
    #list of city limit coordinates, by section
    boxlist=[box for box in limits if len(box)>2]
    return boxlist

#makes a dataframe of floodplains that overlap the property
def get_creek_prop_overlap(prop_polygon_list):
    df_fp_city = pd.read_pickle('/home/amzalucha/mysite/fp_city.pkl')
    fp_coors_list=list(df_fp_city["geometry.coordinates"])
    fp_geo_type=list(df_fp_city["geometry.type"])
    fp_name=list(df_fp_city["properties.CREEK"])
    fp_year=list(df_fp_city["properties.ZONEDESC"])
    full_name=[fp_name[i]+' '+fp_year[i] for i in range(len(fp_name))]
    creek_prop_overlap=[]
    yesnocreeks=[]
    for n in range(len(fp_coors_list)):
        creeklist=[];
        fp_coors=fp_coors_list[n]
        if fp_geo_type[n]=="MultiPolygon":
            for row in fp_coors:
                for creek in row:
                    creeklist.append(creek)
        else:
            creeklist=fp_coors
        creek_polygons=[coors_to_polygon_creeks(creek) for creek in creeklist]
        found=False
        for i, cp in enumerate(creek_polygons):
            for prop_polygon in prop_polygon_list:
                if cp.contains(prop_polygon)==True or cp.intersects(prop_polygon):
                    found=True
                    creek_prop_overlap.append(creeklist[i])


        if found==True:
            yesnocreeks.append(True)
            #print("In the "+fp_name[n]+" "+fp_year[n]+" floodplain")
        else:
            yesnocreeks.append(False)
            #print("Not in the "+fp_name[n]+" "+fp_year[n]+" floodplain")


    #this bit is because Goose/Twomile appears twice in the list
    if yesnocreeks[-2] or yesnocreeks[-3]:
        if not yesnocreeks[-2]:
            yesnocreeks[-2]=True
            creek_prop_overlap.append(creeklist[-2])
        if not yesnocreeks[-3]:
            yesnocreeks[-3]=True
            creek_prop_overlap.append(creeklist[-3])
    del yesnocreeks[-2]
    del full_name[-2]



    return creek_prop_overlap,yesnocreeks,full_name



#makes a dataframe of floodplains that overlap the property for 2013
def get_creek_prop_overlap_2013(prop_polygon_list):
    df_fp_city = pd.read_pickle('fp_city_2013.pkl')
    fp_coors_list=list(df_fp_city["geometry.coordinates"])
    fp_geo_type=list(df_fp_city["geometry.type"])
    fp_name=list(df_fp_city["properties.CREEK"])
    #fp_year=list(df_fp_city["properties.ZONEDESC"])
    full_name=fp_name
    creek_prop_overlap=[]
    yesnocreeks=[]
    for n in range(len(fp_coors_list)):
        creeklist=[];
        fp_coors=fp_coors_list[n]
        if fp_geo_type[n]=="MultiPolygon":
            for row in fp_coors:
                for creek in row:
                    creeklist.append(creek)
        else:
            creeklist=fp_coors
        creek_polygons=[coors_to_polygon_creeks(creek) for creek in creeklist]
        found=False
        for i, cp in enumerate(creek_polygons):
            for prop_polygon in prop_polygon_list:
                if cp.contains(prop_polygon)==True or cp.intersects(prop_polygon):
                    found=True
                    creek_prop_overlap.append(creeklist[i])


        if found==True:
            yesnocreeks.append(True)
        else:
            yesnocreeks.append(False)

    return creek_prop_overlap,yesnocreeks,full_name


def plot_map(address):

    prop_dict=get_rental_data()


    inp=address
    prop_polygon_list=coors_to_polygon_prop(prop_dict[inp])

    boxlist=read_limit_data()

    #100 and 500 year floodplains
    creek_prop_overlap,yesnocreeks,full_name=get_creek_prop_overlap(prop_polygon_list)

    #2013 flood extent
    creek_prop_overlap_2013,yesnocreeks_2013,full_name_2013=get_creek_prop_overlap_2013(prop_polygon_list)

    p = figure(plot_width=600, plot_height=600)

    if prop_dict[inp][0]=='Polygon':
        lon,lat=coors_to_lon_lat(prop_dict[inp][1][0])
        lons=lon
        lats=lat
        p.patch(lon, lat, alpha=0.5, line_width=2, color="DarkGoldenrod", fill_alpha=0.5, legend = 'Rental property')
    else:
        coors=prop_dict[inp][1][0]
        lons=[]
        lats=[]
        for item in coors:
            lon,lat=coors_to_lon_lat(item)
            lont=tuple(lon)
            latt=tuple(lat)
            p.patch(lont, latt, alpha=0.5, line_width=2, color="DarkGoldenrod", fill_alpha=0.5, legend = 'Rental property')
            lons.extend(lon)
            lats.extend(lat)
        lons=tuple(lons)
        lats=tuple(lats)

    for creek in creek_prop_overlap:
        lon,lat=coors_to_lon_lat(creek)
        p.patch(lon,lat, alpha=0.5, line_width=2, color="Aqua", fill_alpha=0.5, legend="Intersecting historical floodplains")

    for creek in creek_prop_overlap_2013:
        lon,lat=coors_to_lon_lat(creek)
        p.patch(lon,lat, alpha=0.5, line_width=2, color="Blue", fill_alpha=0.5, legend="Intersecting 2013 flood extent")

    for box in boxlist:
        lon,lat=coors_to_lon_lat(box)
        p.patch(lon, lat, alpha=0.5, line_width=2, color="Black", fill_alpha=0., legend="Boulder city limits")

    p.annulus(np.mean(lons),np.mean(lats), inner_radius=0.01, outer_radius=0.011,
    color="red", alpha=0.8)

    p.xaxis.axis_label = "East longitude (degrees)"
    p.yaxis.axis_label = "North latitude (degrees)"
    p.xaxis.axis_label_text_font_size="14pt"
    p.yaxis.axis_label_text_font_size="14pt"
    p.x_range = Range1d(*(-105.32, -105.15))
    p.y_range=Range1d(*(39.94,40.1))

    p.legend.location = "bottom_right"
    p.axis.major_label_text_font_size="12pt"

    script, div = components(p)

    ##show(p)
    return script, div, yesnocreeks,full_name, yesnocreeks_2013,full_name_2013
    ##return


@app.route('/graph')#output
def graph():

        address_unformatted = request.args.get('address', '')

        address=format_address(address_unformatted)

        if address=="error":
            return redirect("static/error.html", code=302)

        intersections=make_count_pie(address)

        # Create the plot
        script, div, yesnocreeks,full_name, yesnocreeks_2013,full_name_2013 = plot_map(address)

        nameandyesno=list(zip(full_name,yesnocreeks))

        nameandyesno_2013=list(zip(full_name_2013,yesnocreeks_2013))




        # Embed plot into HTML via Flask Render
        return render_template("graph.html", script=script, div=div, nameandyesno=nameandyesno, intersections=intersections, nameandyesno_2013=nameandyesno_2013)
        ##return



if __name__ == '__main__':
  app.run(port=33507)
