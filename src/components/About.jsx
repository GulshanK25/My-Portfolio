import React from "react";

const About = () => {
  return (
    <div id="about" className="w-full h-screen bg-gradient-to-b from-gray-800 to-black text-white">
      <div className="max-w-screen-lg p-4 mx-auto flex flex-col justify-center w-full h-full">
        <div className="pb-8">
          <h2 className="text-4xl font-bold inline border-b-4 border-gray-500">About Me</h2>
        </div>

        <p className="text-lg leading-loose">
          Hi there! My name is Gulshan Kumar, and I'm a 23-year-old enthusiast with a passion for technology
          and software engineering. I embarked on my journey in this field driven by a genuine interest in
          development and coding, inspired by both personal experiences and familial influences.
        </p>
        <br />

        <p className="text-lg leading-loose">
          As I continue my academic pursuit, I find myself increasingly captivated by the vast and ever-evolving
          landscape of technology. I thrive on tackling new challenges, viewing them as opportunities for growth
          and innovation. I believe in the importance of not only working hard but also working smart, employing
          creativity and determination in every endeavor.
        </p>
      </div>
    </div>
  );
};


export default About;
