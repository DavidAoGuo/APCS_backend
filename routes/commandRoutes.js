const express = require('express');
const router = express.Router();
const Command = require('../models/Command');
const Device = require('../models/Device');
const SensorData = require('../models/SensorData');
const { protect } = require('../middleware/authMiddleware');

// Get all commands for user's devices
router.get('/', protect, async (req, res) => {
  try {
    // Get user's devices
    const devices = await Device.find({ userId: req.user._id });
    
    if (devices.length === 0) {
      return res.status(200).json({
        success: true,
        data: []
      });
    }
    
    const deviceIds = devices.map(device => device._id);
    
    // Get commands for these devices
    const commands = await Command.find({
      deviceId: { $in: deviceIds }
    }).sort({ timestamp: -1 }).limit(50);
    
    return res.status(200).json({
      success: true,
      data: commands
    });
  } catch (error) {
    console.error('Error fetching commands:', error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
});

// Get pending commands for a device (for hardware team)
router.get('/pending/:deviceId', protect, async (req, res) => {
  try {
    const { deviceId } = req.params;
    
    // Verify device belongs to user
    const device = await Device.findOne({
      _id: deviceId,
      userId: req.user._id
    });
    
    if (!device) {
      return res.status(404).json({
        success: false,
        message: 'Device not found or not authorized'
      });
    }
    
    // Get pending commands
    const commands = await Command.find({
      deviceId,
      status: 'pending'
    }).sort({ timestamp: 1 });
    
    return res.status(200).json({
      success: true,
      data: commands
    });
  } catch (error) {
    console.error('Error fetching commands:', error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
});

// Update command status and report sensor reading (for hardware team)
router.post('/update/:commandId', protect, async (req, res) => {
  try {
    const { commandId } = req.params;
    const { status, sensorType, sensorValue } = req.body;
    
    // Find command
    const command = await Command.findById(commandId);
    
    if (!command) {
      return res.status(404).json({
        success: false,
        message: 'Command not found'
      });
    }
    
    // Verify device belongs to user
    const device = await Device.findOne({
      _id: command.deviceId,
      userId: req.user._id
    });
    
    if (!device) {
      return res.status(404).json({
        success: false,
        message: 'Device not found or not authorized'
      });
    }
    
    // Update command status
    command.status = status;
    await command.save();
    
    // If sensor data is provided, update it
    if (sensorType && sensorValue !== undefined) {
      // Create new sensor reading
      await SensorData.create({
        deviceId: command.deviceId,
        type: sensorType,
        value: sensorValue
      });
    }
    
    return res.status(200).json({
      success: true,
      data: command
    });
  } catch (error) {
    console.error('Error updating command:', error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
});

module.exports = router;