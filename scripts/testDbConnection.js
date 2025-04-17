require('dotenv').config();
const mongoose = require('mongoose');
const config = require('../config/config');

async function testConnection() {
  try {
    console.log('Attempting to connect to MongoDB Atlas...');
    const conn = await mongoose.connect(config.MONGO_URI);
    console.log(`MongoDB Connected: ${conn.connection.host}`);
    process.exit(0);
  } catch (error) {
    console.error(`Error connecting to MongoDB: ${error.message}`);
    process.exit(1);
  }
}

testConnection();