import os
import re

filepath = r"c:\Users\Admin\Downloads\fitness tracker\fitness tracker\tracker\templates\tracker\dashboard.html"
with open(filepath, 'r') as f:
    content = f.read()

# We want to replace the `activity-feed` div contents.
# Let's find: `{% if recent_workouts %}` and replace it down to its `{% endif %}`.
# Wait, the structure is:
# {% if recent_workouts %}
# <div class="activity-feed">
#     {% for workout in recent_workouts %}
#     ...
#     {% endfor %}
# </div>
# {% else %}
# <div class="text-center p-5">
# ...
# {% endif %}

old_start = "{% if recent_workouts %}"
old_end = "{% endif %}\n        </div>\n    </div>\n\n    <!-- Right Column: Goals and Daily Stats -->"

idx_start = content.find(old_start)
idx_end = content.find(old_end) + len("{% endif %}")

if idx_start == -1 or idx_end == -1:
    print("Could not find bounds")
else:
    new_feed = """{% if recent_activities %}
            <div class="activity-feed">
                {% for activity in recent_activities %}
                <div class="activity-item">
                    <div class="activity-header">
                        {% if activity.user.profile_picture %}
                        <img src="{{ activity.user.profile_picture.url }}" alt="Profile" class="rounded-circle me-3" style="width: 40px; height: 40px; object-fit: cover;">
                        {% else %}
                        <div class="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center me-3" style="width: 40px; height: 40px; font-weight: bold;">
                            {{ activity.user.username|make_list|first|upper }}
                        </div>
                        {% endif %}
                        <div>
                            <div class="fw-bold" style="font-size: 0.95rem;">{{ activity.user.username }}</div>
                            <div class="text-muted" style="font-size: 0.8rem;">{{ activity.date|date:"F d, Y" }}</div>
                        </div>
                    </div>
                    
                    <div class="ps-5 ms-2">
                        {% if activity.is_cardio %}
                        <!-- CARDIO SESSION RENDERING -->
                        <div class="d-flex justify-content-between align-items-start gap-3">
                            <div class="activity-title">{{ activity.get_activity_type_display }} <i class="fa-solid fa-shoe-prints text-muted ms-2" style="font-size: 1rem;"></i></div>
                            {% if activity.user == request.user %}
                            <div class="d-flex gap-2">
                                <a href="{% url 'edit_cardio' activity.id %}" class="btn btn-sm btn-outline-secondary">Edit</a>
                                <form method="post" action="{% url 'delete_cardio' activity.id %}" onsubmit="return confirm('Delete this session?');">
                                    {% csrf_token %}
                                    <button type="submit" class="btn btn-sm btn-outline-danger">Delete</button>
                                </form>
                            </div>
                            {% endif %}
                        </div>
                        
                        {% if activity.notes %}
                        <p class="mb-3 text-dark" style="font-size: 0.95rem;">{{ activity.notes }}</p>
                        {% endif %}

                        <div class="d-flex gap-4 mt-2 mb-3">
                            <div>
                                <div class="stat-label">Distance</div>
                                <div class="stat-value">{% if activity.distance_km %}{{ activity.distance_km|floatformat:2 }} km{% else %}-{% endif %}</div>
                            </div>
                            <div>
                                <div class="stat-label">Pace</div>
                                <div class="stat-value">{% if activity.pace_per_km %}{{ activity.pace_per_km }}{% else %}-{% endif %}</div>
                            </div>
                            <div>
                                <div class="stat-label">Time</div>
                                <div class="stat-value">{{ activity.duration_minutes }} min</div>
                            </div>
                        </div>

                        {% if activity.map_polyline or True %}
                        <!-- Mock map container (always render for demo) -->
                        <div class="mb-3 rounded-4 overflow-hidden shadow-sm border" style="height: 250px; background: #e9ecef; position: relative;">
                            <div id="map-{{ activity.id }}" class="w-100 h-100 map-container" data-polyline="{{ activity.map_polyline|default:'_p~iF~ps|U_ulLnnqC_mqNvxq`@' }}"></div>
                        </div>
                        {% endif %}

                        {% else %}
                        <!-- WORKOUT SESSION RENDERING -->
                        <div class="d-flex justify-content-between align-items-start gap-3">
                            <div class="activity-title">Afternoon Workout <i class="fa-solid fa-dumbbell text-muted ms-2" style="font-size: 1rem;"></i></div>
                            {% if activity.user == request.user %}
                            <div class="d-flex gap-2">
                                <a href="{% url 'edit_workout' activity.id %}" class="btn btn-sm btn-outline-secondary">Edit</a>
                                <form method="post" action="{% url 'delete_workout' activity.id %}" onsubmit="return confirm('Delete this workout?');">
                                    {% csrf_token %}
                                    <button type="submit" class="btn btn-sm btn-outline-danger">Delete</button>
                                </form>
                            </div>
                            {% endif %}
                        </div>
                        {% if activity.notes %}
                        <p class="mb-3 text-dark" style="font-size: 0.95rem;">{{ activity.notes }}</p>
                        {% endif %}

                        {% if activity.duration_minutes %}
                        <p class="text-muted mb-3">
                            <i class="fa-regular fa-clock me-1"></i>{{ activity.duration_minutes }} mins
                        </p>
                        {% endif %}
                        
                        {% if activity.image %}
                        <div class="mb-3 rounded overflow-hidden shadow-sm" style="max-height: 400px; display: flex; align-items: center; justify-content: center; background: #000;">
                            <img src="{{ activity.image.url }}" alt="Workout Photo" class="img-fluid" style="max-height: 400px; width: 100%; object-fit: contain;">
                        </div>
                        {% endif %}

                        <div class="d-flex gap-5 mt-2 mb-3">
                            <div>
                                <div class="stat-label">Sets</div>
                                <div class="stat-value">{{ activity.sets.count }}</div>
                            </div>
                            <div>
                                <div class="stat-label">Exercises</div>
                                <div style="font-size: 1.1rem; font-weight: 500; line-height: 1.6; margin-top: 5px;">
                                    {% for set in activity.sets.all|slice:":2" %}
                                    <span class="d-inline-block px-2 py-1 bg-light rounded-2 me-1 mb-1 shadow-sm border border-light" style="font-size: 0.85rem;">{{ set.exercise.name }}</span>
                                    {% empty %}
                                    <span class="text-muted">None</span>
                                    {% endfor %}
                                    {% if activity.sets.count > 2 %}
                                    <span class="d-inline-block text-muted px-2 py-1" style="font-size: 0.85rem;">+ {{ activity.sets.count|add:"-2" }} more</span>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if not activity.is_cardio %}
                    <div class="action-bar border-top pt-3 mt-3">
                        {% csrf_token %}
                        <!-- Kudos Button -->
                        <button class="action-btn kudo-btn" data-workout-id="{{ activity.id }}">
                            {% if request.user in activity.kudos.all %}
                                <i class="fa-solid fa-thumbs-up text-primary kudo-icon"></i> 
                            {% else %}
                                <i class="fa-regular fa-thumbs-up kudo-icon"></i> 
                            {% endif %}
                            <span class="kudo-text">Kudos</span> 
                            <span class="kudo-count badge bg-secondary ms-1">{{ activity.kudos.count }}</span>
                        </button>
                        
                        <!-- Comment Toggle Button -->
                        <button class="action-btn comment-toggle-btn" data-workout-id="{{ activity.id }}">
                            <i class="fa-regular fa-comment"></i> Comment 
                            <span class="comment-count badge bg-secondary ms-1">{{ activity.comments.count }}</span>
                        </button>
                    </div>

                    <!-- Hidden Comment Section -->
                    <div class="comment-section mt-3 pt-3 border-top" id="comments-{{ activity.id }}" style="display: none; background: rgba(0,0,0,0.1); padding: 15px; border-radius: 8px;">
                        <div class="comments-list mb-3" id="comments-list-{{ activity.id }}">
                            {% for comment in activity.comments.all %}
                            <div class="mb-2">
                                <span class="fw-bold text-light" style="font-size: 0.9rem;">{{ comment.user.username }}</span>
                                <span class="text-secondary ms-2" style="font-size: 0.8rem;">{{ comment.created_at|date:"M d, P" }}</span>
                                <p class="mb-0 text-white-50" style="font-size: 0.95rem;">{{ comment.text }}</p>
                            </div>
                            {% endfor %}
                        </div>
                        <div class="d-flex gap-2">
                            <input type="text" class="form-control form-control-sm comment-input" id="comment-input-{{ activity.id }}" placeholder="Add a comment...">
                            <button class="btn btn-primary btn-sm submit-comment-btn" data-workout-id="{{ activity.id }}">Post</button>
                        </div>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="text-center p-5">
                <i class="fa-solid fa-ghost fs-1 text-muted mb-3 opacity-50"></i>
                <h5 class="text-muted">No activities yet</h5>
                <p class="text-muted small">When you complete workouts or runs, they'll show up here.</p>
                <a href="{% url 'log_workout' %}" class="btn btn-outline-primary mt-2">Log a Workout</a>
            </div>
            {% endif %}"""

    new_content = content[:idx_start] + new_feed + content[idx_end:]
    with open(filepath, 'w') as f:
        f.write(new_content)
    print("Done")
