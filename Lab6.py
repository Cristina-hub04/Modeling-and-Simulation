import pygame
import random
import matplotlib.pyplot as plt


# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600

# Colors
BACKGROUND_COLOR = (30, 30, 30)
PREY_COLOR = (0, 255, 0)
PREDATOR_COLOR = (255, 0, 0)
FOOD_COLOR = (0, 150, 255)
OBSTACLE_COLOR = (150, 150, 150)
TEXT_COLOR = (200, 200, 200)
ENERGY_BAR_BG = (50, 50, 50)

# Frame rate
FPS = 60

# Initialize screen and clock
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Predator-Prey Simulation")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 24)


def safe_normalize(vec):
    if vec.length_squared() == 0:
        return pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
    return vec.normalize()



# Obstacle class 
class Obstacle:
    def __init__(self, position=None, radius=30):
        self.position = position or pygame.math.Vector2(random.uniform(radius, WIDTH-radius),
                                                        random.uniform(radius, HEIGHT-radius))
        self.radius = radius

    def draw(self):
        pygame.draw.circle(screen, OBSTACLE_COLOR, (int(self.position.x), int(self.position.y)), self.radius)



# Food class
class Food:
    def __init__(self):
        self.position = pygame.math.Vector2(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
        self.radius = 3
        self.color = FOOD_COLOR

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), self.radius)



# Base Agent Class
class Agent:
    def __init__(self, position=None, velocity=None, speed=2, color=PREY_COLOR, max_energy=200):
        self.position = position or pygame.math.Vector2(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
        self.velocity = velocity or pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
        self.speed = speed
        self.color = color
        self.trail = []
        self.max_trail_length = 10
        self.energy = max_energy * 0.5
        self.max_energy = max_energy
        self.mating_timer = 0
        self.mating_partner = None
        self.reproduction_cooldown = 0
        self.radius = 6 

    def update_position(self, simulation):
        # Move agent
        self.position += self.velocity * self.speed

        # Bounce off screen edges
        if self.position.x < 0 or self.position.x > WIDTH:
            self.velocity.x *= -1
        if self.position.y < 0 or self.position.y > HEIGHT:
            self.velocity.y *= -1
        self.position.x = max(0, min(self.position.x, WIDTH))
        self.position.y = max(0, min(self.position.y, HEIGHT))

        # Avoid obstacles
        self.avoid_obstacles(simulation.obstacles)

        # Update trail
        self.trail.append(self.position.copy())
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def avoid_obstacles(self, obstacles):
        for obs in obstacles:
            offset = self.position - obs.position
            dist = offset.length()
            min_dist = self.radius + obs.radius
            if dist < min_dist:
                if dist == 0:
                    push_dir = pygame.math.Vector2(1, 0).rotate(random.uniform(0, 360))
                else:
                    push_dir = offset.normalize()
                overlap = min_dist - dist
                self.position += push_dir * overlap
                # Remove inward velocity component
                inward = self.velocity.dot(push_dir)
                if inward < 0:
                    self.velocity -= push_dir * inward
                # Small nudge
                self.velocity += push_dir * 0.05
                if self.velocity.length_squared() > 0:
                    self.velocity = self.velocity.normalize()

    def draw_trail(self):
        if len(self.trail) > 1:
            pygame.draw.lines(screen, self.color, False, [(int(p.x), int(p.y)) for p in self.trail], 1)

    def draw_energy_bar(self, offset_y=8, width=20, height=4):
        val = max(0.0, min(1.0, self.energy / self.max_energy))
        bx = int(self.position.x - width // 2)
        by = int(self.position.y - offset_y)
        pygame.draw.rect(screen, ENERGY_BAR_BG, (bx, by, width, height))
        fill_col = (0, 255, 0) if val > 0.4 else (255, 165, 0) if val > 0.15 else (255, 0, 0)
        pygame.draw.rect(screen, fill_col, (bx, by, int(width * val), height))


# Prey class

class Prey(Agent):
    def __init__(self):
        super().__init__(speed=2, color=PREY_COLOR, max_energy=200)
        self.vision_radius = 50


       
# Flocking behaviour
   
    def flock(self, prey_list):
        neighbor_radius = 50       
        separation_radius = 20     
        alignment_weight = 0.5
        cohesion_weight = 0.3
        separation_weight = 1.0

        alignment = pygame.math.Vector2()
        cohesion = pygame.math.Vector2()
        separation = pygame.math.Vector2()
        total = 0

        for other in prey_list:
            if other is self:
                continue
            dist = self.position.distance_to(other.position)
            if dist < neighbor_radius:
                alignment += other.velocity
                cohesion += other.position
                total += 1
                if dist < separation_radius:
                    # Push away strongly from close neighbors
                    diff = self.position - other.position
                    if diff.length_squared() > 0:
                        separation += diff / dist

        if total > 0:
            # ALIGNMENT 
            if alignment.length_squared() > 0:
                alignment = alignment.normalize() * alignment_weight

            # COHESION
            cohesion_vec = (cohesion / total) - self.position
            if cohesion_vec.length_squared() > 0:
                cohesion = cohesion_vec.normalize() * cohesion_weight
            else:
                cohesion = pygame.math.Vector2()

            # SEPARATION
            if separation.length_squared() > 0:
                separation = separation.normalize() * separation_weight
            else:
                separation = pygame.math.Vector2()

            # Combine forces
            flock_force = alignment + cohesion + separation

            if flock_force.length_squared() > 0:
                self.velocity = safe_normalize(self.velocity + flock_force * 0.2)

            # Slight speed increase based on flock size
            if total > 10:
                self.speed = 2.7
            elif total > 5:
                self.speed = 2.3
            else:
                self.speed = 2.0


    def update(self, predators, food_list, prey_list, simulation):
        self.energy -= 0.03
        if self.energy <= 0:
            return "dead"

        # Mating
        if self.mating_timer > 0:
            self.mating_timer -= 1
            if self.mating_timer <= 0 and self.mating_partner:
                simulation.spawn_prey(self, self.mating_partner)
                self.energy -= 30
                self.mating_partner.energy -= 30
                self.reproduction_cooldown = 100
                self.mating_partner.reproduction_cooldown = 100
                self.mating_partner.mating_partner = None
                self.mating_partner = None
            return

        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1
    # Flocking behavior
        self.flock(prey_list)

        # Flee predators
        nearest_pred = self._nearest(predators, self.vision_radius)
        if nearest_pred:
            self.velocity = safe_normalize(self.position - nearest_pred.position)
        else:
            # Seek food if low energy
            if self.energy < 80:
                food = self._nearest(food_list, 200)
                if food:
                    self.velocity = safe_normalize(food.position - self.position)

        # Seek mate if high energy
        if self.energy > 120 and self.reproduction_cooldown <= 0:
            for p in prey_list:
                if p is not self and p.energy > 120 and p.mating_timer == 0 and self.position.distance_to(p.position) < 20:
                    self.mating_partner = p
                    self.mating_timer = 60
                    p.mating_partner = self
                    p.mating_timer = 60
                    break

        # Update movement
        self.update_position(simulation)

    def _nearest(self, objects, max_dist):
        nearest = None
        min_d = max_dist
        for obj in objects:
            d = self.position.distance_to(obj.position)
            if d < min_d:
                min_d = d
                nearest = obj
        return nearest

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), 4)
        self.draw_trail()
        self.draw_energy_bar(offset_y=10, width=10, height=3)


# Predator Class
class Predator(Agent):
    def __init__(self):
        super().__init__(speed=3, color=PREDATOR_COLOR, max_energy=400)

    def update(self, prey_list, predator_list, simulation):
        self.energy -= 0.06
        if self.energy <= 0:
            return "dead"

        # Mating
        if self.mating_timer > 0:
            self.mating_timer -= 1
            if self.mating_timer <= 0 and self.mating_partner:
                simulation.spawn_predator(self, self.mating_partner)
                self.energy -= 50
                self.mating_partner.energy -= 50
                self.reproduction_cooldown = 200
                self.mating_partner.reproduction_cooldown = 200
                self.mating_partner.mating_partner = None
                self.mating_partner = None
            return

        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1

        # Hunt prey
        nearest_prey = self._nearest(prey_list, 300)
        if nearest_prey:
            self.velocity = safe_normalize(nearest_prey.position - self.position)
        else:
            # Random wander
            if random.random() < 0.02:
                self.velocity = safe_normalize(self.velocity + pygame.math.Vector2(random.uniform(-0.5,0.5), random.uniform(-0.5,0.5)))

        # Seek mate if high energy
        if self.energy > 300 and self.reproduction_cooldown <= 0:
            for p in predator_list:
                if p is not self and p.energy > 300 and p.mating_timer == 0 and self.position.distance_to(p.position) < 20:
                    self.mating_partner = p
                    self.mating_timer = 300
                    p.mating_partner = self
                    p.mating_timer = 300
                    break

        self.update_position(simulation)

    def _nearest(self, objects, max_dist):
        nearest = None
        min_d = max_dist
        for obj in objects:
            d = self.position.distance_to(obj.position)
            if d < min_d:
                min_d = d
                nearest = obj
        return nearest

    def draw(self):
        angle = self.velocity.angle_to(pygame.math.Vector2(1, 0))
        pts = [pygame.math.Vector2(10,0), pygame.math.Vector2(-6,-6), pygame.math.Vector2(-6,6)]
        rotated = [self.position + p.rotate(-angle) for p in pts]
        pygame.draw.polygon(screen, self.color, [(int(p.x), int(p.y)) for p in rotated])
        self.draw_trail()
        self.draw_energy_bar(offset_y=12, width=12, height=3)


# Simulation
class Simulation:
    def __init__(self, num_prey=50, num_predators=3, num_food=80):
        self.prey_list = [Prey() for _ in range(num_prey)]
        self.predator_list = [Predator() for _ in range(num_predators)]
        self.food_list = [Food() for _ in range(num_food)]
        self.running = True
        self.food_timer = 0
        self.total_born_prey = 0
        self.total_born_pred = 0
        self.obstacles = []

        # History tracking
        self.history_prey = []
        self.history_predator = []
        self.history_born_prey = []
        self.history_born_predator = []
        self.history_food = []
        self.history_prey_births = []
        self.history_pred_births = []
        self.prey_births = 0
        self.pred_births = 0

   
    # Reproduction
  
    def spawn_prey(self, parent1, parent2):
        pos = (parent1.position + parent2.position) / 2
        offset = pygame.math.Vector2(random.uniform(-10, 10), random.uniform(-10, 10))
        child = Prey()
        child.position = pos + offset
        self.prey_list.append(child)
        self.prey_births += 1
        self.total_born_prey += 1

    def spawn_predator(self, parent1, parent2):
        pos = (parent1.position + parent2.position) / 2
        offset = pygame.math.Vector2(random.uniform(-10, 10), random.uniform(-10, 10))
        child = Predator()
        child.position = pos + offset
        self.predator_list.append(child)
        self.pred_births += 1
        self.total_born_pred += 1

    
    # Main loop
    
    def run(self):
        while self.running:
            clock.tick(FPS)
            self.handle_events()
            self.update_agents()
            self.handle_collisions()
            self.spawn_food()

            
            # Record History
          
            self.history_prey.append(len(self.prey_list))
            self.history_predator.append(len(self.predator_list))
            self.history_born_prey.append(self.total_born_prey)
            self.history_born_predator.append(self.total_born_pred)
            self.history_food.append(len(self.food_list))
            self.history_prey_births.append(self.prey_births)
            self.history_pred_births.append(self.pred_births)

            
            # Render
           
            self.render()

        pygame.quit()

       
        # Plotting
        
        plt.figure(figsize=(12,5))

        plt.subplot(1,2,1)
        plt.plot(self.history_prey, label='Prey Population', color='green')
        plt.plot(self.history_predator, label='Predator Population', color='red')
        plt.plot(self.history_food, label='Food Count', color='blue')
        plt.xlabel('Timestep')
        plt.ylabel('Count')
        plt.title('Population Over Time')
        plt.legend()

        plt.subplot(1,2,2)
        plt.plot(self.history_born_prey, label='Prey Births (total)', color='green')
        plt.plot(self.history_born_predator, label='Predator Births (total)', color='red')
        plt.xlabel('Timestep')
        plt.ylabel('Birth Count')
        plt.title('Births Over Time')
        plt.legend()

        plt.tight_layout()
        plt.show()

   
    # Event handling
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.add_prey()
                elif event.key == pygame.K_o:
                    self.add_predator()
                elif event.key == pygame.K_f:
                    for _ in range(10):
                        self.food_list.append(Food())
                elif event.key == pygame.K_b:
                    self.add_obstacle()
                elif event.key == pygame.K_n:
                    self.remove_obstacle()

    def add_prey(self):
        self.prey_list.append(Prey())
        self.total_born_prey += 1

    def add_predator(self):
        self.predator_list.append(Predator())
        self.total_born_pred += 1

    def add_obstacle(self):
        self.obstacles.append(Obstacle())

    def remove_obstacle(self):
        if self.obstacles:
            self.obstacles.pop()

    
    # Update agents
   
    def update_agents(self):
        for prey in self.prey_list[:]:
            status = prey.update(self.predator_list, self.food_list, self.prey_list, self)
            if status == "dead":
                self.prey_list.remove(prey)

        for predator in self.predator_list[:]:
            status = predator.update(self.prey_list, self.predator_list, self)
            if status == "dead":
                self.predator_list.remove(predator)

   
    # Collisions
   
    def handle_collisions(self):
        for prey in self.prey_list[:]:
            for food in self.food_list[:]:
                if prey.position.distance_to(food.position) < 6:
                    prey.energy = min(prey.max_energy, prey.energy + 30)
                    self.food_list.remove(food)
                    break

        for predator in self.predator_list[:]:
            for prey in self.prey_list[:]:
                if predator.position.distance_to(prey.position) < 8:
                    predator.energy = min(predator.max_energy, predator.energy + 80)
                    self.prey_list.remove(prey)
                    break

    # Spawn food periodically
    
    def spawn_food(self):
        self.food_timer += 1
        if self.food_timer >= 30:
            self.food_timer = 0
            if len(self.food_list) < 300:
                for _ in range(random.randint(1, 4)):
                    self.food_list.append(Food())

    
    # Rendering
    
    def render(self):
        screen.fill(BACKGROUND_COLOR)
        self.draw_legend()
        self.draw_stats()
        for food in self.food_list:
            food.draw()
        for prey in self.prey_list:
            prey.draw()
        for predator in self.predator_list:
            predator.draw()
        for obs in self.obstacles:
            obs.draw()
        pygame.display.flip()

    def draw_legend(self):
        prey_text = FONT.render('Prey (Green) - Press P to add', True, PREY_COLOR)
        predator_text = FONT.render('Predator (Red) - Press O to add', True, PREDATOR_COLOR)
        food_text = FONT.render('Food (Blue) - Press F to add', True, FOOD_COLOR)
        obstacle_text = FONT.render('Obstacle (Gray) - Press B to add, N to remove', True, OBSTACLE_COLOR)
        screen.blit(prey_text, (10, 10))
        screen.blit(predator_text, (10, 30))
        screen.blit(food_text, (10, 50))
        screen.blit(obstacle_text, (10, 70))

    def draw_stats(self):
        prey_count_text = FONT.render(f'Prey Count: {len(self.prey_list)}', True, TEXT_COLOR)
        predator_count_text = FONT.render(f'Predator Count: {len(self.predator_list)}', True, TEXT_COLOR)
        screen.blit(prey_count_text, (WIDTH - 150, 10))
        screen.blit(predator_count_text, (WIDTH - 150, 30))



if __name__ == "__main__":
    simulation = Simulation()
    simulation.run()
