const express = require('express');
const router = express.Router();
const { 
  getSchedules, 
  createSchedule,
  updateSchedule,
  deleteSchedule,
  toggleSchedule
} = require('../controllers/scheduleController');
const { protect } = require('../middleware/authMiddleware');

// All routes are protected
router.use(protect);

router.route('/')
  .get(getSchedules)
  .post(createSchedule);

router.route('/:id')
  .put(updateSchedule)
  .delete(deleteSchedule);

router.patch('/:id/toggle', toggleSchedule);

module.exports = router;