require('dotenv').config();
const mongoose = require('mongoose');
const User = require('../models/User');
const Device = require('../models/Device');
const SensorData = require('../models/SensorData');
const connectDB = require('../config/db');

async function generateHistoricalData() {
  try {
    // Connect to database
    await connectDB();
    
    console.log('Connected to MongoDB');
    
    // Find demo user
    const demoUser = await User.findOne({ email: 'demo@example.com' });
    
    if (!demoUser) {
      console.log('Demo user not found. Please run the server first to create a demo user.');
      process.exit(1);
    }
    
    // Find demo device
    const demoDevice = await Device.findOne({ userId: demoUser._id });
    
    if (!demoDevice) {
      console.log('Demo device not found. Please run the server first to create a demo device.');
      process.exit(1);
    }
    
    // Generate 30 days of historical data
    console.log('Generating 30 days of historical data...');
    
    const now = new Date();
    const sensorTypes = ['food', 'water', 'temperature', 'humidity'];
    const historicalData = [];
    
    // For each day in the past 30 days
    for (let day = 30; day >= 0; day--) {
      const date = new Date(now);
      date.setDate(date.getDate() - day);
      date.setHours(0, 0, 0, 0);
      
      // 3 readings per day for each sensor type
      for (let i = 0; i < 3; i++) {
        const hour = 8 + (i * 6); // Readings at 8am, 2pm, 8pm
        date.setHours(hour);
        
        for (const type of sensorTypes) {
          let value;
          
          switch (type) {
            case 'food':
              // Decreasing pattern, refilled every 5 days
              value = day % 5 === 0 ? 100 : Math.max(10, 100 - (day % 5) * 20 - i * 5);
              break;
            case 'water':
              // Decreasing pattern, refilled every 3 days
              value = day % 3 === 0 ? 100 : Math.max(15, 100 - (day % 3) * 25 - i * 8);
              break;
            case 'temperature':
              // Fluctuating between 20-26°C with a slight daily pattern
              value = 23 + Math.sin((day + i/3) * 0.5) * 3;
              value = parseFloat(value.toFixed(1));
              break;
            case 'humidity':
              // Fluctuating between 45-65%
              value = 55 + Math.sin((day + i/3) * 0.7) * 10;
              value = Math.round(value);
              break;
          }
          
          historicalData.push({
            deviceId: demoDevice._id,
            type,
            value,
            timestamp: new Date(date)
          });
        }
      }
    }
    
    // Delete existing historical data
    console.log('Cleaning existing historical data...');
    await SensorData.deleteMany({
      deviceId: demoDevice._id,
      timestamp: { $lt: now }
    });
    
    // Insert historical data
    console.log(`Inserting ${historicalData.length} historical data points...`);
    await SensorData.insertMany(historicalData);
    
    console.log('Historical data generation complete!');
    process.exit(0);
  } catch (error) {
    console.error('Error generating historical data:', error);
    process.exit(1);
  }
}

generateHistoricalData();