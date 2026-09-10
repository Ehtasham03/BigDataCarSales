import pandas as pd
import json
import os

# -
# LOAD DATA
# -
df = pd.read_csv("/Users/Ehtasham/projectLSDDA/Data/CarSales_Dataset.csv")

# ensure new folder
out_dir = "normalized_v5"
os.makedirs(out_dir, exist_ok=True)

# -
# CLEANING & BASIC PROCESSING
# -
def clean_date(series):
    return pd.to_datetime(series, errors='coerce', dayfirst=True).dt.date

df["Date_of_Service"] = clean_date(df["Date_of_Service"])
df["Date_of_Accident"] = clean_date(df["Date_of_Accident"])

df["Cost_of_Service"] = pd.to_numeric(df["Cost_of_Service"], errors="coerce")
df["Cost_of_Repair"] = pd.to_numeric(df["Cost_of_Repair"], errors="coerce")

# -
# MANUFACTURER TABLE
# -
manufacturers = (
    df[["Manufacturer"]]
    .drop_duplicates()
    .sort_values("Manufacturer")
    .reset_index(drop=True)
    .reset_index()
)
manufacturers.rename(columns={"index": "ManufacturerID"}, inplace=True)
manufacturers.to_csv(f"{out_dir}/manufacturers.csv", index=False)

manufacturer_map = dict(zip(
    manufacturers["Manufacturer"], manufacturers["ManufacturerID"]
))
df["ManufacturerID"] = df["Manufacturer"].map(manufacturer_map)

# -
# DEALERS TABLE
# -
dealers = (
    df[["DealerName", "DealerCity", "Latitude", "Longitude"]]
    .drop_duplicates()
    .sort_values(["DealerName"])
    .reset_index(drop=True)
    .reset_index()
)
dealers.rename(columns={"index": "DealerID"}, inplace=True)
dealers.to_csv(f"{out_dir}/dealers.csv", index=False)

dealer_map = dict(zip(
    dealers["DealerName"], dealers["DealerID"]
))
df["DealerID"] = df["DealerName"].map(dealer_map)

# --
# CARS TABLE
# --
cars = df[
    [
        "CarID", "ManufacturerID", "Model", "Engine size",
        "Fuel_Type", "Year_of_Manufacturing", "Mileage",
        "Price", "DealerID"
    ]
].drop_duplicates()

cars.columns = [
    "CarID", "ManufacturerID", "Model", "EngineSize", "FuelType",
    "YearOfManufacture", "Mileage", "Price", "DealerID"
]

cars.to_csv(f"{out_dir}/cars.csv", index=False)

# --
# FEATURES TABLE
# -
features = (
    df[["Features"]]
    .drop_duplicates()
    .reset_index(drop=True)
    .reset_index()
)
features.rename(columns={"index": "FeatureID", "Features": "FeatureName"}, inplace=True)
features.to_csv(f"{out_dir}/features.csv", index=False)

feature_map = dict(zip(
    features["FeatureName"], features["FeatureID"]
))

car_features = df[["CarID", "Features"]].copy()
car_features["FeatureID"] = car_features["Features"].map(feature_map)
car_features = car_features[["CarID", "FeatureID"]].drop_duplicates()

car_features.to_csv(f"{out_dir}/car_features.csv", index=False)

# -
# SERVICE RECORDS TABLE
# -
service_records = df[
    ["ServiceID", "CarID", "Date_of_Service", "ServiceType", "Cost_of_Service"]
].dropna(subset=["ServiceID"])

service_records = service_records.drop_duplicates(
    subset=["CarID", "Date_of_Service", "ServiceType", "Cost_of_Service"],
    keep="first"
)

service_records.columns = ["ServiceID", "CarID", "Date", "Type", "Cost"]
service_records.to_csv(f"{out_dir}/service_records.csv", index=False)

# -
# ACCIDENT RECORDS TABLE
# -
accident_records = df[
    ["AccidentID", "CarID", "Date_of_Accident", "Severity", "Description", "Cost_of_Repair"]
].dropna(subset=["AccidentID"])

accident_records = accident_records.drop_duplicates(
    subset=["CarID", "Date_of_Accident", "Severity", "Description", "Cost_of_Repair"],
    keep="first"
)

accident_records.columns = ["AccidentID", "CarID", "Date", "Severity", "Description", "RepairCost"]
accident_records.to_csv(f"{out_dir}/accident_records.csv", index=False)

# -------------------------------------------
# MONGODB   JSON    EXPORT
# ------------------------------------------------------------------------------
mongo_docs = []

for car_id, group in df.groupby("CarID"):
    car = cars[cars.CarID == car_id].iloc[0].to_dict()

    # Manufacturer details
    manu_row = manufacturers.loc[
        manufacturers["ManufacturerID"] == car["ManufacturerID"]
    ].iloc[0].to_dict()

    manufacturer_info = {
        "manufacturerId": manu_row["ManufacturerID"],
        "name": manu_row["Manufacturer"]
    }

    # Dealer details
    dealer_row = dealers.loc[
        dealers["DealerID"] == car["DealerID"]
    ].iloc[0].to_dict()

    dealer_info = {
        "dealerId": dealer_row["DealerID"],
        "name": dealer_row["DealerName"],
        "city": dealer_row["DealerCity"],
        "location": {
            "latitude": dealer_row["Latitude"],
            "longitude": dealer_row["Longitude"]
        }
    }

    # Features
    feature_ids = car_features[car_features.CarID == car_id]["FeatureID"].tolist()
    feature_list = features[features.FeatureID.isin(feature_ids)]["FeatureName"].tolist()

    # Services
    services = group[
        ["ServiceID", "Date_of_Service", "ServiceType", "Cost_of_Service"]
    ].dropna(subset=["ServiceID"]).drop_duplicates()

    service_list = [
        {
            "serviceId": s.ServiceID,
            "date": str(s.Date_of_Service),
            "type": s.ServiceType,
            "cost": s.Cost_of_Service,
        }
        for _, s in services.iterrows()
    ]

    # Accidents
    accidents = group[
        ["AccidentID", "Date_of_Accident", "Severity", "Description", "Cost_of_Repair"]
    ].dropna(subset=["AccidentID"]).drop_duplicates()

    accident_list = [
        {
            "accidentId": a.AccidentID,
            "date": str(a.Date_of_Accident),
            "severity": a.Severity,
            "description": a.Description,
            "repairCost": a.Cost_of_Repair,
        }
        for _, a in accidents.iterrows()
    ]

    # Final MongoDB document
    doc = {
        **car,
        "manufacturer": manufacturer_info,
        "dealer": dealer_info,
        "features": feature_list,
        "serviceHistory": service_list,
        "accidentHistory": accident_list,
    }

    mongo_docs.append(doc)

with open(f"{out_dir}/mongo_car_documents.json", "w") as f:
    json.dump(mongo_docs, f, indent=4)

print("Normalization complete. Files written to 'normalized_v5' directory.")