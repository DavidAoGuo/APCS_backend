const Schedule = require('../models/Schedule');
const Device = require('../models/Device');

// @desc    Get all schedules
// @route   GET /api/schedules
// @access  Private
const getSchedules = async (req, res) => {
  try {
    // Get user's devices
    const devices = await Device.find({ userId: req.user._id });
    
    if (devices.length === 0) {
      return res.status(200).json({
        success: true,
        data: []
      });
    }
    
    // Get device IDs
    const deviceIds = devices.map(device => device._id);
    
    // Find all schedules for the user's devices
    const schedules = await Schedule.find({
      deviceId: { $in: deviceIds }
    }).sort({ time: 1 });
    
    return res.status(200).json({
      success: true,
      data: schedules
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Create a schedule
// @route   POST /api/schedules
// @access  Private
const createSchedule = async (req, res) => {
  try {
    const { type, time, days, amount, enabled } = req.body;
    
    // Validate type
    if (!type || !['food', 'water'].includes(type)) {
        return res.status(400).json({
            success: false,
            message: 'Invalid schedule type. Must be food or water.'
          });
        }
        
        // Validate time
        if (!time || !/^([01]\d|2[0-3]):([0-5]\d)$/.test(time)) {
          return res.status(400).json({
            success: false,
            message: 'Invalid time format. Must be HH:MM (24-hour format).'
          });
        }
        
        // Validate days
        const validDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        if (!days || !Array.isArray(days) || days.length === 0 || !days.every(day => validDays.includes(day))) {
          return res.status(400).json({
            success: false,
            message: 'Invalid days. Must include at least one valid day of the week.'
          });
        }
        
        // Validate amount
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
        const deviceId = devices[0]._id;
        
        // Create new schedule
        const schedule = await Schedule.create({
          deviceId,
          type,
          time,
          days,
          amount,
          enabled: enabled !== undefined ? enabled : true
        });
        
        return res.status(201).json({
          success: true,
          data: schedule
        });
      } catch (error) {
        console.error(error);
        return res.status(500).json({
          success: false,
          message: 'Server error'
        });
      }
    };
    
    // @desc    Update a schedule
    // @route   PUT /api/schedules/:id
    // @access  Private
    const updateSchedule = async (req, res) => {
      try {
        const { id } = req.params;
        const { type, time, days, amount, enabled } = req.body;
        
        // Get user's devices
        const devices = await Device.find({ userId: req.user._id });
        
        if (devices.length === 0) {
          return res.status(404).json({
            success: false,
            message: 'No devices found'
          });
        }
        
        // Get device IDs
        const deviceIds = devices.map(device => device._id);
        
        // Find schedule by ID and check if it belongs to user's device
        const schedule = await Schedule.findOne({
          _id: id,
          deviceId: { $in: deviceIds }
        });
        
        if (!schedule) {
          return res.status(404).json({
            success: false,
            message: 'Schedule not found'
          });
        }
        
        // Update fields if provided
        if (type && ['food', 'water'].includes(type)) {
          schedule.type = type;
        }
        
        if (time && /^([01]\d|2[0-3]):([0-5]\d)$/.test(time)) {
          schedule.time = time;
        }
        
        const validDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        if (days && Array.isArray(days) && days.length > 0 && days.every(day => validDays.includes(day))) {
          schedule.days = days;
        }
        
        if (amount && amount > 0 && amount <= 100) {
          schedule.amount = amount;
        }
        
        if (enabled !== undefined) {
          schedule.enabled = enabled;
        }
        
        // Save updated schedule
        await schedule.save();
        
        return res.status(200).json({
          success: true,
          data: schedule
        });
      } catch (error) {
        console.error(error);
        return res.status(500).json({
          success: false,
          message: 'Server error'
        });
      }
    };
    
    // @desc    Delete a schedule
    // @route   DELETE /api/schedules/:id
    // @access  Private
    const deleteSchedule = async (req, res) => {
      try {
        const { id } = req.params;
        
        // Get user's devices
        const devices = await Device.find({ userId: req.user._id });
        
        if (devices.length === 0) {
          return res.status(404).json({
            success: false,
            message: 'No devices found'
          });
        }
        
        // Get device IDs
        const deviceIds = devices.map(device => device._id);
        
        // Find and delete schedule
        const schedule = await Schedule.findOneAndDelete({
          _id: id,
          deviceId: { $in: deviceIds }
        });
        
        if (!schedule) {
          return res.status(404).json({
            success: false,
            message: 'Schedule not found'
          });
        }
        
        return res.status(200).json({
          success: true,
          message: 'Schedule deleted successfully'
        });
      } catch (error) {
        console.error(error);
        return res.status(500).json({
          success: false,
          message: 'Server error'
        });
      }
    };
    
    // @desc    Toggle schedule enabled status
    // @route   PATCH /api/schedules/:id/toggle
    // @access  Private
    const toggleSchedule = async (req, res) => {
      try {
        const { id } = req.params;
        const { enabled } = req.body;
        
        if (enabled === undefined) {
          return res.status(400).json({
            success: false,
            message: 'Enabled status is required'
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
        
        // Get device IDs
        const deviceIds = devices.map(device => device._id);
        
        // Find schedule by ID and check if it belongs to user's device
        const schedule = await Schedule.findOne({
          _id: id,
          deviceId: { $in: deviceIds }
        });
        
        if (!schedule) {
          return res.status(404).json({
            success: false,
            message: 'Schedule not found'
          });
        }
        
        // Update enabled status
        schedule.enabled = enabled;
        
        // Save updated schedule
        await schedule.save();
        
        return res.status(200).json({
          success: true,
          data: schedule
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
      getSchedules,
      createSchedule,
      updateSchedule,
      deleteSchedule,
      toggleSchedule
    };