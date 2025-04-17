const Device = require('../models/Device');
const SensorData = require('../models/SensorData');
const mqttService = require('../services/mqttService');
const Command = require('../models/Command');

console.log('Controller module loaded');

// @desc    Dispense food
// @route   POST /api/control/dispense-food
// @access  Private
const dispenseFood = async (req, res) => {
  console.log('⚡ DISPENSE FOOD ENDPOINT CALLED');
  
  try {
    const { amount } = req.body;
    
    console.log('⚡ Request body:', req.body);
    
    if (!amount || amount <= 0 || amount > 100) {
      console.log('⚡ Invalid amount:', amount);
      return res.status(400).json({
        success: false,
        message: 'Invalid amount. Must be between 1 and 100.'
      });
    }
    
    // Get user's devices
    console.log('⚡ Looking for devices for user:', req.user._id);
    const devices = await Device.find({ userId: req.user._id });
    
    if (devices.length === 0) {
      console.log('⚡ No devices found for user');
      return res.status(404).json({
        success: false,
        message: 'No devices found'
      });
    }
    
    // Get the primary device (first one for now)
    const device = devices[0];
    console.log('⚡ Using device:', device._id, device.name);
    
    if (device.status !== 'online') {
      console.log('⚡ Device is not online:', device.status);
      return res.status(400).json({
        success: false,
        message: 'Device is offline or in maintenance'
      });
    }
    
    console.log('⚡ Creating command record');
    // Create a command record in the database
    const command = await Command.create({
      deviceId: device._id,
      type: 'dispenseFood',
      value: amount || 0,
      status: 'pending'
    });
    
    console.log(`⚡ Command record created: ${command._id}`);
    
    // Use direct MQTT publishing like in our test script
    console.log('⚡ Setting up direct MQTT connection');
    
    const mqtt = require('mqtt');
    const directClient = mqtt.connect('mqtt://test.mosquitto.org', {
      clientId: `direct_food_${Math.random().toString(16).substring(2, 10)}`,
      clean: true
    });
    
    directClient.on('connect', function() {
      console.log('⚡ Direct MQTT client connected');
      
      // Publish the command
      directClient.publish('/seniorDesign/s2c', 'F0', { qos: 1, retain: false }, function(err) {
        if (err) {
          console.error('⚡ Failed to publish command:', err);
          
          // Update command status to failed
          Command.findByIdAndUpdate(command._id, { status: 'failed' }).catch(err => {
            console.error('⚡ Error updating command status:', err);
          });
          
          return res.status(500).json({
            success: false,
            message: 'Failed to send command to device'
          });
        } 
        
        console.log('⚡ Successfully published F0 command');
        
        // Update command status to processing
        Command.findByIdAndUpdate(command._id, { status: 'processing' }).catch(err => {
          console.error('⚡ Error updating command status:', err);
        });
        
        // Send success response
        res.status(200).json({
          success: true,
          message: 'Food dispense command sent successfully',
          data: {
            amount
          }
        });
        
        // Close the connection
        setTimeout(() => {
          directClient.end();
          console.log('⚡ Direct MQTT client disconnected');
        }, 1000);
      });
    });
    
    directClient.on('error', function(err) {
      console.error('⚡ MQTT Error:', err);
      
      // Update command status to failed
      Command.findByIdAndUpdate(command._id, { status: 'failed' }).catch(err => {
        console.error('⚡ Error updating command status:', err);
      });
      
      return res.status(500).json({
        success: false,
        message: 'MQTT connection error'
      });
    });
    
  } catch (error) {
    console.error('⚡ ERROR in dispenseFood:', error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Dispense water
// @route   POST /api/control/dispense-water
// @access  Private
const dispenseWater = async (req, res) => {
  try {
    const { amount } = req.body;
    
    if (!amount || amount <= 0 || amount > 100) {
      return res.status(400).json({
        success: false,
        message: 'Invalid amount. Must be between 1 and 100.'
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
    const device = devices[0];
    
    if (device.status !== 'online') {
      return res.status(400).json({
        success: false,
        message: 'Device is offline or in maintenance'
      });
    }
    
    // Send command to hardware via MQTT
    const commandSent = await mqttService.sendCommand('dispenseWater', amount, device._id);
    
    if (!commandSent) {
      return res.status(500).json({
        success: false,
        message: 'Failed to send command to device'
      });
    }
    
    return res.status(200).json({
      success: true,
      message: 'Water dispense command sent successfully',
      data: {
        amount
      }
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Set temperature
// @route   POST /api/control/set-temperature
// @access  Private
const setTemperature = async (req, res) => {
  try {
    const { temperature } = req.body;
    
    if (temperature === undefined || temperature < 15 || temperature > 30) {
      return res.status(400).json({
        success: false,
        message: 'Invalid temperature. Must be between 15°C and 30°C.'
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
    const device = devices[0];
    
    if (device.status !== 'online') {
      return res.status(400).json({
        success: false,
        message: 'Device is offline or in maintenance'
      });
    }
    
    // Send command to hardware via MQTT
    const commandSent = await mqttService.sendCommand('setTemperature', temperature, device._id);
    
    if (!commandSent) {
      return res.status(500).json({
        success: false,
        message: 'Failed to send command to device'
      });
    }
    
    return res.status(200).json({
      success: true,
      message: 'Temperature setting command sent successfully',
      data: {
        temperature
      }
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Test MQTT command
// @route   GET /api/control/test-mqtt
// @access  Public
const testMqtt = async (req, res) => {
  console.log('⚡ TEST MQTT ENDPOINT CALLED');
  
  try {
    // Create a fresh client for testing
    const mqtt = require('mqtt');
    const client = mqtt.connect('mqtt://test.mosquitto.org', {
      clientId: 'test_client_' + Math.random().toString(16).substring(2, 8),
      clean: true
    });
    
    client.on('connect', () => {
      console.log('⚡ Test client connected');
      
      client.publish('/seniorDesign/s2c', 'TEST-FROM-ENDPOINT', { qos: 1, retain: false }, (err) => {
        if (err) {
          console.error('⚡ Test publish failed:', err);
          res.status(500).json({ success: false, message: 'Failed to publish test message' });
        } else {
          console.log('⚡ Test message published successfully');
          res.status(200).json({ success: true, message: 'Test message published successfully' });
        }
        
        setTimeout(() => {
          client.end();
          console.log('⚡ Test client disconnected');
        }, 1000);
      });
    });
    
    client.on('error', (err) => {
      console.error('⚡ Test client error:', err);
      res.status(500).json({ success: false, message: 'MQTT connection error' });
    });
  } catch (error) {
    console.error('⚡ ERROR in testMqtt:', error);
    res.status(500).json({ success: false, message: 'Server error' });
  }
};

module.exports = {
  dispenseFood,
  dispenseWater,
  setTemperature,
  testMqtt
};