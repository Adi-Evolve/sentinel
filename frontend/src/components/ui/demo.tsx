import { CosmicParallaxBg } from "@/components/ui/parallax-cosmic-background";

const DemoOne = () => {
  return (
    <div className="flex w-full h-screen justify-center items-center">
      <CosmicParallaxBg 
        head="EaseMize" 
        text="Easy, customizeable, Best" 
        loop={true}
      />
    </div>
  );
};

export { DemoOne };
