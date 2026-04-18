"use client";

import React, { useEffect, useRef } from "react";
import { motion, useAnimation } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import * as THREE from "three";

type WovenLightHeroProps = {
  headline?: string;
  subtitle?: string;
  description?: string;
  buttonLabel?: string;
  brandLabel?: string;
  onExplore?: () => void;
};

export const WovenLightHero = ({
  headline = "Log-Sentinel",
  subtitle = "Woven by Threat Intelligence",
  description = "Offline cybersecurity triage using hybrid detection (rules + Isolation Forest + spike analytics), with timeline evidence and export-ready incident briefs.",
  buttonLabel = "Open Detection Dashboard",
  brandLabel = "LOG SENTINEL",
  onExplore,
}: WovenLightHeroProps) => {
  const textControls = useAnimation();
  const buttonControls = useAnimation();

  useEffect(() => {
    const link = document.createElement("link");
    link.href =
      "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap";
    link.rel = "stylesheet";
    document.head.appendChild(link);

    return () => {
      document.head.removeChild(link);
    };
  }, []);

  return (
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden bg-black">
      <div className="absolute inset-0 z-0">
        <video 
          autoPlay 
          loop 
          muted 
          playsInline 
          className="h-full w-full object-cover pointer-events-none"
        >
          <source src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260217_030345_246c0224-10a4-422c-b324-070b7c0eceda.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-black/50" />
      </div>
      <HeroNav brandLabel={brandLabel} />

      <div className="relative z-10 mx-auto max-w-5xl px-6 text-center">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { delay: 0.3, duration: 0.8 } }}
          className="mb-4 text-xs tracking-[0.20em] text-cyan-300/70 uppercase font-semibold"
          style={{ fontFamily: "'Inter', sans-serif" }}
        >
          Advanced Cyber Defense Template
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0, transition: { delay: 0.5, duration: 0.9 } }}
          className="text-6xl font-bold text-white md:text-8xl tracking-tight"
          style={{
            fontFamily: "'Inter', sans-serif",
            letterSpacing: "-0.02em",
          }}
        >
          {headline}
        </motion.h1>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0, transition: { delay: 0.7, duration: 0.9 } }}
          className="mx-auto mt-6 max-w-3xl text-2xl font-semibold text-cyan-200/90 md:text-3xl tracking-tight"
          style={{ fontFamily: "'Inter', sans-serif", letterSpacing: "-0.01em" }}
        >
          {subtitle}
        </motion.h2>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { delay: 0.9, duration: 0.8 } }}
          className="mx-auto mt-8 max-w-2xl text-base text-slate-300 md:text-lg leading-relaxed"
          style={{ fontFamily: "'Inter', sans-serif" }}
        >
          {description}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0, transition: { delay: 1.1, duration: 0.8 } }}
          className="mt-14 flex flex-col sm:flex-row w-full items-center justify-center gap-5"
        >
          <button
            type="button"
            onClick={onExplore}
            className="w-full sm:w-auto px-10 py-3 bg-cyan-500/90 hover:bg-cyan-400/95 text-white font-semibold text-base rounded-lg transition-all duration-200 hover:shadow-[0_8px_24px_rgba(34,211,238,0.3)] hover:-translate-y-1 active:translate-y-0 shadow-[0_4px_12px_rgba(34,211,238,0.2)]"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            Go to Dashboard
          </button>
          <button
            type="button"
            onClick={() => {
              const aboutSection = document.getElementById("about-log-sentinel");
              if (aboutSection) {
                aboutSection.scrollIntoView({ behavior: "smooth" });
              } else {
                window.location.href = "/about";
              }
            }}
            className="w-full sm:w-auto px-10 py-3 border-2 border-slate-500/50 hover:border-slate-400 text-white font-semibold text-base rounded-lg transition-all duration-200 bg-transparent hover:bg-slate-800/30 active:bg-slate-800/50"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            Learn More
          </button>
        </motion.div>
      </div>
    </div>
  );
};

type HeroNavProps = {
  brandLabel: string;
};

const HeroNav = ({ brandLabel }: HeroNavProps) => {
  return (
    <motion.nav
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0, transition: { delay: 0.2, duration: 0.6 } }}
      className="absolute left-0 right-0 top-0 z-20 p-6 backdrop-blur-sm"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-cyan-300" />
          <span
            className="text-sm font-bold tracking-widest text-white uppercase"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            {brandLabel}
          </span>
        </div>
      </div>
    </motion.nav>
  );
};

const WovenCanvas = ({ position = "center" }: { position?: "left" | "right" | "center" }) => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) {
      return;
    }

    const container = mountRef.current;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const mouse = new THREE.Vector2(0, 0);
    const clock = new THREE.Clock();
    const particleCount = 15000; // Reduced for performance with two canvases

    const positions = new Float32Array(particleCount * 3);
    const originalPositions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const velocities = new Float32Array(particleCount * 3);

    const geometry = new THREE.BufferGeometry();
    const torusKnot = new THREE.TorusKnotGeometry(1.5, 0.5, 200, 32);

    for (let i = 0; i < particleCount; i += 1) {
      const vertexIndex = i % torusKnot.attributes.position.count;
      const x = torusKnot.attributes.position.getX(vertexIndex);
      const y = torusKnot.attributes.position.getY(vertexIndex);
      const z = torusKnot.attributes.position.getZ(vertexIndex);

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      originalPositions[i * 3] = x;
      originalPositions[i * 3 + 1] = y;
      originalPositions[i * 3 + 2] = z;

      const color = new THREE.Color();
      color.setHSL(Math.random(), 0.8, 0.62);
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;

      velocities[i * 3] = 0;
      velocities[i * 3 + 1] = 0;
      velocities[i * 3 + 2] = 0;
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 0.02,
      vertexColors: true,
      blending: THREE.AdditiveBlending,
      transparent: true,
      opacity: 0.85,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    const currentPos = new THREE.Vector3();
    const originalPos = new THREE.Vector3();
    const velocity = new THREE.Vector3();
    const direction = new THREE.Vector3();
    const returnForce = new THREE.Vector3();
    const mouseWorld = new THREE.Vector3();

    const handleMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    };

    window.addEventListener("mousemove", handleMouseMove);

    let frameId = 0;
    const animate = () => {
      frameId = window.requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();
      mouseWorld.set(mouse.x * 3, mouse.y * 3, 0);

      for (let i = 0; i < particleCount; i += 1) {
        const ix = i * 3;
        const iy = i * 3 + 1;
        const iz = i * 3 + 2;

        currentPos.set(positions[ix], positions[iy], positions[iz]);
        originalPos.set(originalPositions[ix], originalPositions[iy], originalPositions[iz]);
        velocity.set(velocities[ix], velocities[iy], velocities[iz]);

        const dist = currentPos.distanceTo(mouseWorld);
        if (dist < 1.5) {
          const force = (1.5 - dist) * 0.01;
          direction.subVectors(currentPos, mouseWorld).normalize();
          velocity.add(direction.multiplyScalar(force));
        }

        returnForce.subVectors(originalPos, currentPos).multiplyScalar(0.001);
        velocity.add(returnForce);
        velocity.multiplyScalar(0.95);

        positions[ix] += velocity.x;
        positions[iy] += velocity.y;
        positions[iz] += velocity.z;

        velocities[ix] = velocity.x;
        velocities[iy] = velocity.y;
        velocities[iz] = velocity.z;
      }

      geometry.attributes.position.needsUpdate = true;
      points.rotation.y = elapsedTime * 0.05;
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      container.removeChild(renderer.domElement);
      geometry.dispose();
      material.dispose();
      torusKnot.dispose();
      renderer.dispose();
    };
  }, []);

  const canvasClasses = {
    left: "absolute top-0 left-0 h-full w-1/3 z-0",
    right: "absolute top-0 right-0 h-full w-1/3 z-0",
    center: "absolute inset-0 z-0",
  };

  return <div ref={mountRef} className={canvasClasses[position]} />;
};
