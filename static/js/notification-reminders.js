/**
 * Notification Reminder System
 * 
 * Handles periodic polling for unread notifications and plays sound alerts
 * according to the reminder mechanism (every 10 minutes for unread notifications).
 * 
 * Features:
 * - Polls for unread notifications requiring reminders every 5 minutes
 * - Plays a gentle notification beep using Web Audio API
 * - Updates reminder timestamps when sounds are played
 * - Automatically stops reminders when notifications are marked as read
 */

class NotificationReminder {
    constructor(config = {}) {
        this.config = {
            pollInterval: config.pollInterval || 5 * 60 * 1000, // 5 minutes in milliseconds
            apiEndpoint: config.apiEndpoint || '/notifications/api/unread-for-reminders/',
            audioContext: null,
            enabled: config.enabled !== false,
            debug: config.debug || false,
        };

        // Derive enabled once so both config and state start from the same value.
        const enabled = config.enabled !== false;
        this.config.enabled = enabled;

        this.state = {
            isPolling: false,
            pollTimerId: null,
            soundTimerId: null,
            notificationsForReminder: [],
            soundEnabled: enabled,
        };

        this.init();
    }

    /**
     * Initialize the reminder system
     */
    init() {
        if (!this.config.enabled) {
            this.debug('Notification reminders disabled');
            return;
        }

        try {
            // Initialize Web Audio API context
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.config.audioContext = new AudioContext();
            this.debug('Audio context initialized');
        } catch (e) {
            console.warn('Web Audio API not available:', e);
        }

        // Start polling immediately and then every interval
        this.pollForReminders();
        this.state.pollTimerId = setInterval(() => {
            this.pollForReminders();
        }, this.config.pollInterval);

        this.debug(`Notification reminder polling started (interval: ${this.config.pollInterval}ms)`);
    }

    /**
     * Poll the server for unread notifications that need reminders
     */
    async pollForReminders() {
        try {
            const response = await fetch(this.config.apiEndpoint);
            const data = await response.json();

            this.state.notificationsForReminder = data.notifications || [];

            if (data.count > 0) {
                this.debug(`${data.count} notification(s) need reminders`);
                this.playReminders();
            }
        } catch (error) {
            console.error('Failed to poll reminders:', error);
        }
    }

    /**
     * Play reminder sounds and show alerts for unread notifications
     */
    playReminders() {
        if (this.state.notificationsForReminder.length === 0) {
            return;
        }

        // Group notifications by type for smarter UX
        const notificationsByType = this.groupByType(this.state.notificationsForReminder);

        // Play sound and show desktop notification for first few
        this.state.notificationsForReminder.slice(0, 3).forEach((notif, index) => {
            // Stagger the sounds slightly for multiple notifications
            setTimeout(() => {
                this.playNotificationSound();
                this.showBrowserNotification(notif);
                this.updateReminderTimestamp(notif.id);
            }, index * 300); // 300ms between each notification
        });

        // Show summary if there are many
        if (this.state.notificationsForReminder.length > 3) {
            this.showReminderSummary(this.state.notificationsForReminder);
        }
    }

    /**
     * Play a notification sound using Web Audio API
     */
    playNotificationSound() {
        // Primary mute gate — set by stop(), cleared by resume().
        if (!this.state.soundEnabled) {
            this.debug('Sound is muted — skipping playback');
            return;
        }

        // Lazily create the AudioContext when first needed.
        // This covers two cases:
        //   (a) init() was skipped because enabled:false at construction time.
        //   (b) The browser has not yet created one (should not normally happen).
        if (!this.config.audioContext) {
            try {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                this.config.audioContext = new AudioContext();
            } catch (e) {
                console.warn('Web Audio API not available:', e);
                return;
            }
        }

        const ctx = this.config.audioContext;

        const doPlay = () => {
            try {
                const now = ctx.currentTime;
                const oscillator = ctx.createOscillator();
                const gainNode   = ctx.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(ctx.destination);

                // Two-tone beep for recognition
                oscillator.frequency.setValueAtTime(800,  now);
                oscillator.frequency.setValueAtTime(1000, now + 0.1);

                gainNode.gain.setValueAtTime(0.3, now);
                gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

                oscillator.start(now);
                oscillator.stop(now + 0.5);

                this.debug('Notification sound played');
            } catch (error) {
                console.error('Failed to play notification sound:', error);
            }
        };

        // Browsers auto-suspend a new AudioContext until a user gesture has
        // occurred. Resume it first, then play, so the sound is never silently
        // dropped. The soundEnabled gate above already prevents this path from
        // being reached when the user has muted sounds.
        if (ctx.state === 'suspended') {
            ctx.resume().then(doPlay).catch(e => console.error('AudioContext resume failed:', e));
        } else {
            doPlay();
        }
    }

    /**
     * Show a browser desktop notification
     */
    showBrowserNotification(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            try {
                new Notification(notification.title, {
                    body: notification.message,
                    icon: '/static/images/icon-notification.png',
                    tag: `notif-${notification.id}`,
                    requireInteraction: false,
                });
                this.debug(`Browser notification shown: ${notification.title}`);
            } catch (error) {
                console.error('Failed to show browser notification:', error);
            }
        }
    }

    /**
     * Show a summary toast for multiple notifications
     */
    showReminderSummary(notifications) {
        const count = notifications.length;
        const message = `You have ${count} unread notifications`;

        if ('Notification' in window && Notification.permission === 'granted') {
            try {
                new Notification('Reminder', {
                    body: message,
                    tag: 'notif-summary',
                    requireInteraction: false,
                });
                this.debug(`Summary notification shown: ${message}`);
            } catch (error) {
                console.error('Failed to show summary notification:', error);
            }
        }
    }

    /**
     * Update the reminder timestamp for a notification
     */
    async updateReminderTimestamp(notificationId) {
        try {
            const endpoint = `/notifications/api/update-reminder/${notificationId}/`;
            await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                },
            });
            this.debug(`Reminder timestamp updated for notification ${notificationId}`);
        } catch (error) {
            console.error('Failed to update reminder timestamp:', error);
        }
    }

    /**
     * Request permission for browser notifications
     */
    static requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then((permission) => {
                if (permission === 'granted') {
                    new Notification('Notifications Enabled', {
                        body: 'You will now receive unread notification reminders.',
                    });
                }
            });
        }
    }

    /**
     * Stop the reminder polling and mute sounds immediately.
     * soundEnabled = false is checked inside playNotificationSound(), so any
     * staggered setTimeout callbacks already in the queue become no-ops.
     */
    stop() {
        this.state.soundEnabled = false;
        if (this.state.pollTimerId) {
            clearInterval(this.state.pollTimerId);
            this.state.pollTimerId = null;
        }
        this.debug('Notification reminder polling stopped');
    }

    /**
     * Resume the reminder polling and re-enable sounds.
     */
    resume() {
        this.state.soundEnabled = true;
        if (!this.state.pollTimerId) {
            this.pollForReminders();
            this.state.pollTimerId = setInterval(() => {
                this.pollForReminders();
            }, this.config.pollInterval);
        }
        this.debug('Notification reminder polling resumed');
    }

    /**
     * Group notifications by type for smarter display
     */
    groupByType(notifications) {
        return notifications.reduce((acc, notif) => {
            const type = notif.notif_type;
            if (!acc[type]) {
                acc[type] = [];
            }
            acc[type].push(notif);
            return acc;
        }, {});
    }

    /**
     * Get CSRF token from DOM
     */
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Debug logging
     */
    debug(message) {
        if (this.config.debug) {
            console.log(`[NotificationReminder] ${message}`);
        }
    }
}

// Instantiate immediately — this script is loaded with `defer`, so the HTML is
// fully parsed at this point and no DOM access is required here.
// Reading localStorage ensures the user's persisted preference is respected from
// the very first poll rather than defaulting to enabled on every page load.
window.notificationReminder = new NotificationReminder({
    debug: false,
    enabled: localStorage.getItem('soundAlertsEnabled') !== 'false',
});

// Request notification permission on first load
NotificationReminder.requestNotificationPermission();

// Pause polling while the tab is hidden; restore it only when the user's
// preference still allows sounds (prevents visibility events from silently
// re-enabling a toggle the user has turned off).
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        window.notificationReminder.stop();
    } else if (localStorage.getItem('soundAlertsEnabled') !== 'false') {
        window.notificationReminder.resume();
    }
});
