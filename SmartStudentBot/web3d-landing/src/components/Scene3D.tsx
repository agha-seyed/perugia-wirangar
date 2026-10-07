'use client';

import { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { Environment, Float, ContactShadows } from '@react-three/drei';
import * as THREE from 'three';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(ScrollTrigger);

function GeometricGriffin({ groupRef }: { groupRef: React.RefObject<THREE.Group | null> }) {
  // A majestic, abstract geometric representation of the Perugia Griffin.
  // Eagle head, lion body, wings.
  return (
    <group ref={groupRef} position={[0, -1, 0]}>
      <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
        {/* Lion Body */}
        <mesh position={[0, 1, 0]}>
          <boxGeometry args={[1.5, 1, 2.5]} />
          <meshStandardMaterial color="#222" metalness={0.8} roughness={0.2} />
        </mesh>
        
        {/* Legs (Abstract Pillars) */}
        <mesh position={[-0.6, 0, 1]}>
          <cylinderGeometry args={[0.2, 0.1, 1]} />
          <meshStandardMaterial color="#333" metalness={0.9} roughness={0.1} />
        </mesh>
        <mesh position={[0.6, 0, 1]}>
          <cylinderGeometry args={[0.2, 0.1, 1]} />
          <meshStandardMaterial color="#333" metalness={0.9} roughness={0.1} />
        </mesh>
        <mesh position={[-0.6, 0, -1]}>
          <cylinderGeometry args={[0.2, 0.1, 1]} />
          <meshStandardMaterial color="#333" metalness={0.9} roughness={0.1} />
        </mesh>
        <mesh position={[0.6, 0, -1]}>
          <cylinderGeometry args={[0.2, 0.1, 1]} />
          <meshStandardMaterial color="#333" metalness={0.9} roughness={0.1} />
        </mesh>

        {/* Eagle Head & Neck */}
        <mesh position={[0, 2, 1.2]} rotation={[0.2, 0, 0]}>
          <coneGeometry args={[0.5, 1.5, 4]} />
          <meshStandardMaterial color="#c1121f" metalness={0.5} roughness={0.3} emissive="#4a0000" emissiveIntensity={0.5} />
        </mesh>
        <mesh position={[0, 2.6, 1.6]} rotation={[-Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.2, 0.8, 3]} />
          <meshStandardMaterial color="#fdf0d5" metalness={0.9} roughness={0.1} />
        </mesh>

        {/* Wings (Geometric Shards) */}
        <group position={[0, 1.5, -0.5]}>
          <mesh position={[-1.5, 1, 0]} rotation={[0, 0.5, -0.8]}>
            <boxGeometry args={[3, 0.1, 1.5]} />
            <meshStandardMaterial color="#00ffff" metalness={1} roughness={0} emissive="#004444" wireframe />
          </mesh>
          <mesh position={[1.5, 1, 0]} rotation={[0, -0.5, 0.8]}>
            <boxGeometry args={[3, 0.1, 1.5]} />
            <meshStandardMaterial color="#00ffff" metalness={1} roughness={0} emissive="#004444" wireframe />
          </mesh>
        </group>
      </Float>
      <ContactShadows resolution={1024} scale={10} blur={2} opacity={0.5} far={10} color="#00ffff" />
    </group>
  );
}

function ScrollAnimations({ 
  griffinRef, 
  lightRef1, 
  lightRef2 
}: { 
  griffinRef: React.RefObject<THREE.Group | null>;
  lightRef1: React.RefObject<THREE.SpotLight | null>;
  lightRef2: React.RefObject<THREE.SpotLight | null>;
}) {
  useGSAP(() => {
    if (!griffinRef.current || !lightRef1.current || !lightRef2.current) return;

    // Setup GSAP Timeline linked to scroll
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: "#scroll-container",
        start: "top top",
        end: "bottom bottom",
        scrub: 1, // Smooth scrubbing
      }
    });

    // Section 1: Course Management (Rotate and zoom in)
    tl.to(griffinRef.current.rotation, { y: Math.PI, ease: "power1.inOut" }, 0);
    tl.to(griffinRef.current.position, { z: 2, ease: "power1.inOut" }, 0);
    tl.to(lightRef1.current, { intensity: 150 }, 0);

    // Section 2: Campus Tools (Rotate up, zoom out, change color)
    tl.to(griffinRef.current.rotation, { x: 0.5, y: Math.PI * 2, ease: "power1.inOut" }, 1);
    tl.to(griffinRef.current.position, { z: -1, y: 0, ease: "power1.inOut" }, 1);
    tl.to(lightRef1.current, { intensity: 100 }, 1);
    tl.to(lightRef2.current, { intensity: 200 }, 1);

    // Section 3: Student Services (Final hero pose)
    tl.to(griffinRef.current.rotation, { x: 0, y: Math.PI * 2.5, ease: "power1.inOut" }, 2);
    tl.to(griffinRef.current.position, { z: 0, y: -1, ease: "power1.inOut" }, 2);
  });

  return null;
}

export default function Scene3D() {
  const griffinRef = useRef<THREE.Group>(null);
  const lightRef1 = useRef<THREE.SpotLight>(null);
  const lightRef2 = useRef<THREE.SpotLight>(null);

  return (
    <div className="fixed top-0 left-0 w-full h-full -z-10 bg-[#050505]">
      <Canvas camera={{ position: [0, 2, 8], fov: 45 }}>
        <color attach="background" args={['#050505']} />
        <ambientLight intensity={0.5} />
        
        {/* Cinematic Spotlights */}
        <spotLight 
          ref={lightRef1}
          position={[5, 5, 5]} 
          angle={0.4} 
          penumbra={1} 
          intensity={100} 
          color="#00ffff" 
          castShadow 
        />
        <spotLight 
          ref={lightRef2}
          position={[-5, 5, -5]} 
          angle={0.4} 
          penumbra={1} 
          intensity={50} 
          color="#c1121f" 
          castShadow 
        />
        
        <GeometricGriffin groupRef={griffinRef} />
        <ScrollAnimations griffinRef={griffinRef} lightRef1={lightRef1} lightRef2={lightRef2} />
        
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
