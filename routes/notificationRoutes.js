const express = require('express');
const router = express.Router();
const { 
  getNotifications, 
  markNotificationAsRead,
  markAllNotificationsAsRead,
  deleteAllNotifications,
  createNotification
} = require('../controllers/notificationController');
const { protect } = require('../middleware/authMiddleware');

// All routes are protected
router.use(protect);

router.route('/')
  .get(getNotifications)
  .post(createNotification)
  .delete(deleteAllNotifications);

router.patch('/read-all', markAllNotificationsAsRead);
router.patch('/:id/read', markNotificationAsRead);

module.exports = router;