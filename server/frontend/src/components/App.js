/**
 * Created by Ornithopter on 2017/10/9.
 */
import React from "react";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";

class App extends React.Component {
    constructor(props) {
        super(props);
        this.globalStyle = {

        }
    }

    render() {
        return <MuiThemeProvider>
            {this.props.children}
        </MuiThemeProvider>
    }
}

export default App