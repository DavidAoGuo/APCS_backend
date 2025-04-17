const Notification = require('../models/Notification');

// @desc    Get all notifications for a user
// @route   GET /api/notifications
// @access  Private
const getNotifications = async (req, res) => {
  try {
    // Find all notifications for the user
    const notifications = await Notification.find({
      userId: req.user._id
    }).sort({ timestamp: -1 });
    
    return res.status(200).json({
      success: true,
      data: notifications
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Mark notification as read
// @route   PATCH /api/notifications/:id/read
// @access  Private
const markNotificationAsRead = async (req, res) => {
  try {
    const { id } = req.params;
    console.log('Received mark as read request for ID:', id);

    // Find notification by ID and check if it belongs to the user
    const notification = await Notification.findOne({
      _id: id,
      userId: req.user._id
    });
    
    if (!notification) {
      return res.status(404).json({
        success: false,
        message: 'Notification not found'
      });
    }
    
    // Update read status
    notification.read = true;
    
    // Save updated notification
    await notification.save();
    
    return res.status(200).json({
      success: true,
      data: notification
    });
  } catch (error) {
    console.error('Error in markNotificationAsRead:', error);
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Mark all notifications as read
// @route   PATCH /api/notifications/read-all
// @access  Private
const markAllNotificationsAsRead = async (req, res) => {
  try {
    // Update all unread notifications for the user
    const result = await Notification.updateMany(
      { userId: req.user._id, read: false },
      { read: true }
    );
    
    return res.status(200).json({
      success: true,
      message: `${result.modifiedCount} notifications marked as read`,
      data: { modifiedCount: result.modifiedCount }
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Delete all notifications for a user
// @route   DELETE /api/notifications
// @access  Private
const deleteAllNotifications = async (req, res) => {
  try {
    // Delete all notifications for the user
    const result = await Notification.deleteMany({
      userId: req.user._id
    });
    
    return res.status(200).json({
      success: true,
      message: `${result.deletedCount} notifications deleted`,
      data: { deletedCount: result.deletedCount }
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
};

// @desc    Create a notification (for testing/admin purposes)
// @route   POST /api/notifications
// @access  Private
const createNotification = async (req, res) => {
  try {
    const { title, message, type } = req.body;
    
    if (!title || !message) {
      return res.status(400).json({
        success: false,
        message: 'Title and message are required'
      });
    }
    
    // Create new notification
    const notification = await Notification.create({
      userId: req.user._id,
      title,
      message,
      type: type || 'info',
      read: false
    });
    
    return res.status(201).json({
      success: true,
      data: notification
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
  getNotifications,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  deleteAllNotifications,
  createNotification
};