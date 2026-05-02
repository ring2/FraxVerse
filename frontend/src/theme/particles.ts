// Particle effect parameters for the canvas background

export interface ParticleParams {
  count: number;
  speed: number;
  opacity: number;
  sizeMin: number;
  sizeMax: number;
  color: string;
  lineDistance: number;
  lineOpacity: number;
}

export const defaultParticles: ParticleParams = {
  count: 80,
  speed: 0.3,
  opacity: 0.6,
  sizeMin: 1,
  sizeMax: 3,
  color: "#6b5ce7",
  lineDistance: 120,
  lineOpacity: 0.12,
};
