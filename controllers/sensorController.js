const SensorData = require('../models/SensorData');
const Device = require('../models/Device');

// @desc    Get all sensor data for a user
// @route   GET /api/sensors
// @access  Private
const getAllSensorData = async (req, res) => {
  try {
    // Get user's devices
    const devices = await Device.find({ userId: req.user._id });
    
    if (devices.length === 0) {
      return res.status(200).json({
        success: true,
        data: {
          foodLevel: 0,
          waterLevel: 0,
          temperature: 0,
          humidity: 0,
          lastUpdated: null
        }
      });
    }
    
    // Get the primary device (first one for now)
    const deviceId = devices[0]._id;
    
    // Get the latest sensor readings for each type
    const foodData = await SensorData.findOne({ 
      deviceId, 
      type: 'food' 
    }).sort({ timestamp: -1 });
    
    const waterData = await SensorData.findOne({ 
      deviceId, 
      type: 'water' 
    }).sort({ timestamp: -1 });
    
    const temperatureData = await SensorData.findOne({ 
      deviceId, 
      type: 'temperature' 
    }).sort({ timestamp: -1 });
    
    const humidityData = await SensorData.findOne({ 
      deviceId, 
      type: 'humidity' 
    }).sort({ timestamp: -1 });
    
    // Format response
    const responseData = {
      foodLevel: foodData ? foodData.value : 0,
      waterLevel: waterData ? waterData.value : 0,
      temperature: temperatureData ? temperatureData.value : 0,
      humidity: humidityData ? humidityData.value : 0,
      lastUpdated: foodData || waterData || temperatureData || humidityData 
        ? (foodData || waterData || temperatureData || humidityData).timestamp 
        : null
    };
    
    return res.status(200).json({
      success: true,
      data: responseData
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Get sensor history
// @route   GET /api/sensors/history
// @access  Private
const getSensorHistory = async (req, res) => {
  try {
    const { type, range, startDate: customStartDate, endDate: customEndDate } = req.query;
    
    if (!type || !['food', 'water', 'temperature', 'humidity'].includes(type)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid sensor type'
      });
    }
    
    // Get user's devices
    const devices = await Device.find({ userId: req.user._id });
    
    if (devices.length === 0) {
      return res.status(200).json({
        success: true,
        data: []
      });
    }
    
    // Get the primary device (first one for now)
    const deviceId = devices[0]._id;
    
    // Calculate date range
    let startDate;
    let endDate = new Date(); // Default to now
    
    if (range === 'custom' && customStartDate && customEndDate) {
      // For custom range, use provided dates
      startDate = new Date(customStartDate);
      endDate = new Date(customEndDate);
      // Set end date to end of day
      endDate.setHours(23, 59, 59, 999);
    } else {
      // Use predefined ranges
      switch (range) {
        case 'day':
          startDate = new Date();
          startDate.setDate(startDate.getDate() - 1);
          break;
        case 'month':
          startDate = new Date();
          startDate.setMonth(startDate.getMonth() - 1);
          break;
        case 'week':
        default:
          startDate = new Date();
          startDate.setDate(startDate.getDate() - 7);
      }
    }
    
    // Query sensor data in time range
    const sensorData = await SensorData.find({
      deviceId,
      type,
      timestamp: { $gte: startDate, $lte: endDate }
    }).sort({ timestamp: 1 });
    
    // Format data for chart display
    const formattedData = sensorData.map(data => ({
      x: data.timestamp.toISOString().split('T')[0], // Extract date part
      y: data.value
    }));
    
    // For development/testing: generate mock data if no real data available
    if (formattedData.length === 0) {
      // Generate mock data
      const mockData = [];
      const days = (endDate - startDate) / (1000 * 60 * 60 * 24);
      const numPoints = Math.min(Math.ceil(days), 30); // Cap at 30 points
      
      for (let i = 0; i < numPoints; i++) {
        const date = new Date(startDate);
        date.setDate(date.getDate() + i);
        
        let value;
        switch (type) {
          case 'food':
          case 'water':
            value = Math.floor(Math.random() * 40) + 60; // 60-100
            break;
          case 'temperature':
            value = Math.floor(Math.random() * 10) + 18; // 18-28
            break;
          case 'humidity':
            value = Math.floor(Math.random() * 20) + 40; // 40-60
            break;
        }
        
        mockData.push({
          x: date.toISOString().split('T')[0],
          y: value
        });
      }
      
      return res.status(200).json({
        success: true,
        data: mockData
      });
    }
    
    return res.status(200).json({
      success: true,
      data: formattedData
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Add sensor reading (for simulation/testing)
// @route   POST /api/sensors/:type
// @access  Private
const addSensorReading = async (req, res) => {
  try {
    const { type } = req.params;
    const { value } = req.body;
    
    if (!type || !['food', 'water', 'temperature', 'humidity'].includes(type)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid sensor type'
      });
    }
    
    // Get user's devices
    const devices = await Device.find({ userId: req.user._id });
    
    if (devices.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'No devices found'
      });
    }
    
    // Get the primary device (first one for now)
    const deviceId = devices[0]._id;
    
    // Create new sensor reading
    const sensorReading = await SensorData.create({
      deviceId,
      type,
      value
    });
    
    return res.status(201).json({
      success: true,
      data: sensorReading
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

module.exports = {
  getAllSensorData,
  getSensorHistory,
  addSensorReading
};