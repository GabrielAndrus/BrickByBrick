export default function Home() {
  return (
    <>
      <header>
        <div className="header-left">
          <div className="logo-bb">B<span>B</span></div>
          <div className="header-title">Building Blocks</div>
        </div>
        
        <div className="header-center"></div>

        <div className="header-right">
          <div className="icon-box">
            <i className="fa-brands fa-github"></i>
          </div>
          <div className="icon-box">
            <div className="mlh-logo">MLH</div>
          </div>
          <div className="deer-logo">
            <svg viewBox="0 0 24 24">
              <path d="M12 2C8 2 6 5 6 7c0 1.5 1 2.5 1 2.5S5 12 5 14c0 1.5 1 3 3 3 0 0 .5 2 4 2s4-2 4-2c2 0 3-1.5 3-3 0-2-2-4.5-2-4.5s1-1 1-2.5c0-2-2-5-6-5z" fill="none" stroke="#b388ff" strokeWidth="2"/>
              <path d="M8 7l-2-2m10 2l2-2" stroke="#b388ff" strokeWidth="2"/>
            </svg>
          </div>
        </div>
      </header>

      <main>
        <div className="content-wrapper">
          <div className="text-section">
            <h1>Rebuild<br/>your <em>identity,</em></h1>
            <p>
              Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
            </p>
            <p>
              Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
            </p>
          </div>

          <div className="visual-section">
            <div className="lego-stack">
              <div className="brick red-brick">
                <div className="face face-front">PIECE</div>
                <div className="face face-top"></div>
                <div className="face face-side"></div>
              </div>

              <div className="brick blue-brick">
                <div className="face face-front">BY</div>
                <div className="face face-top"></div>
                <div className="face face-side"></div>
              </div>

              <div className="brick gold-brick">
                <div className="face face-front">PIECE</div>
                <div className="face face-top"></div>
                <div className="face face-side"></div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
