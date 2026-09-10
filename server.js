const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");

const app = express();
app.use(express.json());
app.use(cors());
app.use(express.static(__dirname)); // serve current directory
// Route to serve the charts page
app.get('/charts', (req, res) => {
    res.sendFile(__dirname + '/charts.html');
});


const connectionString= "mongodb://localhost:27017/Shop"  //"mongodb+srv://<USER_NAME>:<PASSWORD>@cluster0.zvdyokj.mongodb.net/Shop?retryWrites=true&w=majority";
// Connect to MongoDB Atlas
mongoose.connect(connectionString, {
  family: 4,
  //tls: true
})
.then(() => console.log("✅ Connected to MongoDB database"))
.catch(err => console.error("❌ MongoDB connection error:", err));

// Define Product schema
const productSchema = new mongoose.Schema({
  CarID: String,
  ManufacturerID: Number,
  Model: String,
  EngineSize: Number,
  FuelType: String,
  YearOfManufacture: Number,
  Mileage: Number,
  Price: Number,
  DealerID: Number,

  manufacturer: {
    manufacturerId: Number,
    name: String
  },

  dealer: {
    dealerId: Number,
    name: String,
    city: String,
    location: {
      latitude: Number,
      longitude: Number
    }
  },

  features: [String],

  serviceHistory: [
    {
      serviceId: String,
      date: String,
      type: String,
      cost: Number
    }
  ],

  accidentHistory: [
    {
      accidentId: String,
      date: String,
      severity: String,
      description: String,
      repairCost: Number
    }
  ]
});

// Create model
const Product = mongoose.model('Product', productSchema, 'products');


// API route to get all products
app.get('/products', async (req, res) => {
  try {
    const query = {};
    const { 
      Model, 
      FuelType, 
      minPrice, 
      maxPrice, 
      minYear, 
      maxYear, 
      sort, 
      feature // Ensure this is properly destructured from req.query
    } = req.query;

    console.log('Received query:', req.query);  // Log the query parameters

    // Model search (case-insensitive)
    if (Model) query.Model = { $regex: Model, $options: 'i' };

    // Fuel type filter
    if (FuelType) query.FuelType = FuelType;

    // Price range
    if (minPrice || maxPrice) {
      query.Price = {};
      if (minPrice && !isNaN(minPrice)) query.Price.$gte = Number(minPrice);
      if (maxPrice && !isNaN(maxPrice)) query.Price.$lte = Number(maxPrice);
    }

    // Year range
    if (minYear || maxYear) {
      query.YearOfManufacture = {};
      if (minYear && !isNaN(minYear)) query.YearOfManufacture.$gte = Number(minYear);
      if (maxYear && !isNaN(maxYear)) query.YearOfManufacture.$lte = Number(maxYear);
    }

    // Feature search (if a feature is provided)
    if (feature) {
      query.features = { $in: [feature] };  // Filter cars that have the feature
    }

    // Sorting
    const sortOption = {};
    if (sort === "asc") sortOption.Price = 1;
    if (sort === "desc") sortOption.Price = -1;


    
    const products = await Product.find(query).sort(sortOption);
    res.json(products);
  } catch (err) {
    console.error('Error:', err);  // Log the error
    res.status(500).json({ message: "Error loading cars" });
  }
});



// Start server
const PORT=3000;
app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));